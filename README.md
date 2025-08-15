Objective
Design and implement a snapshot-based state management system for use within the Cua Agent SDK.

This system should:
Capture the state of a running container at defined intervals or events (e.g., start, after each action, at run end).


Restore container state from a chosen snapshot, resuming execution from that point.


Store metadata (timestamp, action context, etc.) with each snapshot in a persistent format.


Integrate cleanly into the SDK’s architecture and callback lifecycle without breaking existing functionality.



Requirements
Support for creating, listing, and restoring snapshots for containers (implementing the Docker Provider is sufficient; other providers can raise NotImplementedError).


Maintain associated metadata for each snapshot, including at least a timestamp and an action or run context.


Implement configurable snapshot retention and cleanup to prevent unbounded storage growth.


Allow developers to control snapshot intervals (manual, every action, start/end of run, etc.).


Use a storage location and metadata format of your choice, as long as it is logical and extensible.


Implement as a pluggable component within the Agent SDK’s callback system so it can be enabled/disabled without code changes elsewhere.



Collaboration & Updates
This task is expected to be collaborative. We’ll create a dedicated Slack channel where you can:
Ask questions


Share progress


Receive feedback


We’d appreciate brief offline updates every 1–2 days, just to stay in sync and help if needed.

Documentation
Refer to https://docs.trycua.com for SDK documentation, message formats, and integration guidelines.

Deliverables
Source code (ideally implemented as a provider extension and/or callback).


Brief documentation outlining your approach, design decisions, and tradeoffs.


Test cases and usage examples demonstrating snapshot creation, listing, restoration, and cleanup.



Timeline
Estimated duration: 1 week
