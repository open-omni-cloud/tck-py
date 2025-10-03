# User Guide: Implementing the Producer Contract

The Producer contract defines the standard interface for providers that publish messages to a topic or queue. It's the entry point for any event-driven communication in the Open Omni-Cloud ecosystem.

This guide details how to implement a compliant message producer by satisfying the `TestProducerContract`.

## Contract Overview

**TCK Class:** ```tck_py.messaging.producer.TestProducerContract```

The `TestProducerContract` validates that a producer can correctly publish messages with a payload, a partitioning key, and custom headers. Unlike simpler contracts, testing a producer requires a way to consume the message to verify its delivery and integrity. This requirement is reflected in the fixture design.

## Implementing the Fixture: `provider_factory`

The `provider_factory` for this contract is more advanced. It needs to provide both the producer to be tested and a way to verify its output.

```info
The factory must return an **async function** that, when awaited, provides a tuple containing:
1.  A ready-to-use **producer instance**.
2.  A helper async function, `get_message_from_topic(topic, timeout)`, which can consume a single message from a given topic for verification purposes.
```

### Example Fixture Implementation

Let's assume you are building a `KafkaProducerProvider`. The fixture would be responsible for creating a producer and also providing a simple, temporary consumer for the TCK's internal use.

```python
# tests/compliance/test_kafka_producer_compliance.py
import pytest
from tck_py.messaging.producer import TestProducerContract
from my_project.providers.kafka_producer import KafkaProducerProvider
# Assume you have a simple consumer for testing
from my_project.utils.kafka_test_consumer import create_test_consumer

class TestKafkaProducerCompliance(TestProducerContract):

    @pytest.fixture
    def provider_factory(self):
        """
        This factory provides the TCK with a Kafka producer and a way
        to verify the messages it sends.
        """
        async def _factory(config: dict | None = None):
            # 1. Create the producer instance
            producer_config = config or {"bootstrap_servers": "localhost:9092"}
            producer = KafkaProducerProvider(config=producer_config)
            await producer.connect() # Assuming an explicit connect method

            # 2. Define the verification helper function
            async def get_message_from_topic(topic: str, timeout: float):
                # This helper creates a short-lived consumer to get one message
                test_consumer = await create_test_consumer(topic)
                try:
                    message = await asyncio.wait_for(test_consumer.get_one(), timeout=timeout)
                    return message
                finally:
                    await test_consumer.close()

            # The concrete implementation of what is returned will vary.
            # Here we assume the test_consumer returns an object with .payload, .key, .headers

            return producer, get_message_from_topic

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `TestProducerContract` and will be run against your provider.

---

### `test_publish_simple_message`

-   **Purpose**: Verifies that a basic message with a binary payload is successfully delivered.
-   **Behavior**: The test calls `await producer.publish(topic, payload)`. It then uses the `get_message_from_topic` helper to consume the message and asserts that the consumed payload is identical to the original.

---

### `test_publish_with_key`

-   **Purpose**: Ensures that a message's partitioning key is correctly transmitted.
-   **Behavior**: The test calls `await producer.publish(topic, payload, key=...)`. The verification consumer then checks that the received message object contains the exact same key.

---

### `test_publish_with_headers`

-   **Purpose**: Validates the transport of metadata via message headers, which is critical for features like distributed tracing.
-   **Behavior**: The test calls `await producer.publish(topic, payload, headers=...)` with a dictionary of headers. The verification consumer must receive a message containing the same key-value pairs in its headers.

---

### `test_publish_to_unavailable_broker_raises_exception`

-   **Purpose**: A critical reliability test to ensure the producer fails predictably.
-   **Behavior**: The TCK calls your `provider_factory` with a configuration pointing to an invalid broker address. It then calls `await producer.publish(...)`.
-   **Requirement**: Your provider **must** detect the connection failure and raise the TCK's standardized ```tck_py.shared.exceptions.PublishError```.
