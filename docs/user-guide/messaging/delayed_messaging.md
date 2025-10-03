# User Guide: Implementing the Delayed Messaging Contract

The Delayed Messaging contract validates one of the advanced resilience patterns of the Open Omni-Cloud standard: the ability to publish a message that will only be delivered after a specified delay.

This functionality is typically implemented via the "Republisher Pattern," where a message is first sent to an intermediate "delay topic" and a background service later republishes it to its final destination topic once the delay has passed. This TCK contract is designed to test this entire end-to-end flow in a provider-agnostic way.

## Contract Overview

**TCK Class:** ```tck_py.messaging.delayed_messaging.TestDelayedMessagingContract```

The `TestDelayedMessagingContract` primarily focuses on time-based verification. It ensures that a message published with a `delay_seconds` parameter is only consumed after that time has elapsed, and that its content and metadata are perfectly preserved.

## Implementing the Fixture: `provider_factory`

The fixture for this contract must orchestrate the entire delayed messaging flow.

```info
The factory must return an **async function** that, when awaited, provides a tuple containing:
1.  An async `publish_func` that accepts a `delay_seconds` parameter. This function is responsible for sending the message into the delay mechanism.
2.  An async helper function, `get_message_from_topic(topic, timeout)`, which listens on the **final destination topic** to verify the message's arrival.
```

Your fixture implementation is responsible for setting up and running the entire underlying infrastructure, including any intermediate topics and the republisher service itself.

### Example Fixture Implementation

A compliant implementation would require setting up the producer, the consumer(s) for the delay topics, and the republisher logic.

```python
# tests/compliance/test_delayed_messaging_compliance.py
import pytest
from tck_py.messaging.delayed_messaging import TestDelayedMessagingContract
from my_project.messaging import DelayedPublisher, TestConsumer # Your components

class TestDelayedMessagingCompliance(TestDelayedMessagingContract):

    @pytest.fixture
    def provider_factory(self):
        """
        This factory provides the TCK with a way to publish delayed messages
        and a way to verify their final delivery.
        """
        async def _factory(**config):
            # 1. Setup the entire delayed messaging infrastructure.
            # This would include starting the republisher service in the background.
            delayed_publisher = await setup_delayed_messaging_system()

            # 2. Define the publish function for the TCK.
            async def publish_func(topic, payload, key, headers, delay_seconds):
                await delayed_publisher.publish(topic, payload, key, headers, delay_seconds)

            # 3. Define the verification helper function.
            async def get_message_from_topic(topic: str, timeout: float):
                # This helper creates a consumer on the final destination topic.
                test_consumer = TestConsumer(topic)
                # ... logic to get one message ...
                return message

            return publish_func, get_message_from_topic

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `TestDelayedMessagingContract` and will be run against your provider.

---

### `test_message_is_delivered_after_delay`

-   **Purpose**: **This is the core test of the contract.** It verifies that the delay mechanism works as intended.
-   **Behavior**: The test records a timestamp, calls `publish()` with a `delay_seconds` of 2.0, and then immediately starts listening on the final destination topic. The test measures the time until the message is consumed.
-   **Requirement**: The total elapsed time **must** be greater than or equal to the requested delay. The test allows for a reasonable buffer (e.g., 1 second) for processing overhead.

---

### `test_message_without_delay_is_delivered_immediately`

-   **Purpose**: A control test to ensure that the delay logic does not interfere with normal, non-delayed messages.
-   **Behavior**: The test calls `publish()` with `delay_seconds=None` or `0`. It asserts that the message is delivered very quickly (e.g., in under 1 second).

---

### `test_delayed_message_retains_key_and_headers`

-   **Purpose**: A critical data integrity test. It verifies that all message metadata is preserved throughout the delay and republishing process.
-   **Behavior**: The test publishes a message with a key and custom headers, along with a delay. When the message is finally consumed from the destination topic, the test asserts that the received key and headers are identical to the ones originally sent.
-   **Requirement**: Your implementation's "envelope" mechanism must correctly store and restore all original message context.
