# User Guide: Implementing the Consumer Contract

The Consumer contract is the counterpart to the Producer. It defines the standard for providers that subscribe to a topic, receive messages, and process them via a handler function. This contract is essential for building reliable, event-driven services.

This guide details how to implement a compliant message consumer by satisfying the `TestConsumerContract`, including its advanced resilience behaviors.

## Contract Overview

**TCK Class:** ```tck_py.messaging.consumer.TestConsumerContract```

The `TestConsumerContract` validates that a consumer correctly receives messages with the expected payload, key, and headers. More importantly, it verifies that the consumer correctly reacts to the processing outcomes returned by the business logic handler (`SUCCESS`, `RETRY`, `FAIL`), ensuring reliable message processing.

## Implementing the Fixture: `provider_factory`

Testing a background process like a consumer requires a carefully orchestrated fixture.

```info
The factory must return an **async function** that accepts the test's `handler` and `topic`. When awaited, this factory must provide a tuple containing:
1.  A **running consumer task** that is already subscribed to the topic and wired to the provided handler.
2.  An async `publish_func` to send messages to the consumer's topic for verification.
3.  An async `get_message_from_dlq` helper to verify the Dead Letter Queue functionality.
```

### Example Fixture Implementation

Let's assume you are building a `KafkaConsumerProvider`. The fixture is responsible for starting the consumer loop in a background task and providing a way to publish test messages to it.

```python
# tests/compliance/test_kafka_consumer_compliance.py
import pytest
import asyncio
from tck_py.messaging.consumer import TestConsumerContract, ProcessingOutcome
from my_project.providers.kafka_consumer import KafkaConsumerProvider
from my_project.utils.kafka_test_producer import create_test_producer # For sending messages

class TestKafkaConsumerCompliance(TestConsumerContract):

    @pytest.fixture
    def provider_factory(self):
        """
        This factory provides the TCK with a running Kafka consumer and
        a producer to send messages to it.
        """
        async def _factory(handler, topic, consumer_config):
            # 1. Create and start the consumer in a background task
            consumer = KafkaConsumerProvider(handler, topic, consumer_config)
            consumer_task = asyncio.create_task(consumer.run())

            # 2. Create a producer to send test messages
            test_producer = await create_test_producer()

            async def publish_func(payload, key, headers):
                await test_producer.publish(topic, payload, key, headers)

            # 3. Create a helper to check the DLQ
            async def get_message_from_dlq(timeout):
                # Logic to consume one message from the DLQ topic
                ...

            return consumer_task, publish_func, get_message_from_dlq

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `TestConsumerContract` and will be run against your provider.

---

### `test_consumes_simple_message`

-   **Purpose**: Verifies the basic message reception loop.
-   **Behavior**: The TCK provides a simple handler that puts the received payload into a queue. The test then publishes a message and waits for the payload to appear in the queue, asserting its content. Your provider must successfully receive the message and invoke the handler.

---

### `test_consumes_message_with_key_and_headers`

-   **Purpose**: Ensures that message metadata (key and headers) is preserved and delivered to the handler correctly.
-   **Behavior**: The test publishes a message with a key and headers. The TCK's handler extracts these from the consumed message object and puts them into a queue for verification. Your provider must construct the message object passed to the handler with all the correct data.

---

### `test_retry_outcome_redelivers_message`

-   **Purpose**: A critical resilience test. It verifies that your consumer wrapper correctly handles a request to retry a message.
-   **Behavior**: The TCK provides a handler that returns `ProcessingOutcome.RETRY` on the first call and `ProcessingOutcome.SUCCESS` on the second.
-   **Requirement**: Your provider, upon receiving the `RETRY` outcome, must **not** acknowledge the message, ensuring that the message broker redelivers it. The test passes only if the handler is called a second time and the message is successfully processed.

---

### `test_fail_outcome_moves_message_to_dlq`

-   **Purpose**: Verifies the ultimate failure handling mechanism: the Dead Letter Queue.
-   **Behavior**: The TCK provides a handler that always returns `ProcessingOutcome.FAIL` (or exceeds the `max_attempts` configured). The test publishes a message and then uses the `get_message_from_dlq` helper.
-   **Requirement**: Your provider must, after exhausting all retry attempts, forward the failed message to the configured DLQ. The test passes by successfully consuming the original message from the DLQ.
