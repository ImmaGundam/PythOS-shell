# Security Model

PythOS Shell is not a security boundary.

It includes a shell-level login gate and basic session handling, but this should not be treated as operating-system-level authentication.

## Password Storage

The project uses a salted SHA-256 password hash for the local shell login gate. The plain-text password is not intended to be stored directly.

## Local File Transformation

Files stored inside the shell user file root may be transformed through a lightweight session-based file obfuscation/encryption mechanism.

This should not be advertised as strong filesystem encryption.

## No Containers or Sandboxing

PythOS Shell does not currently use containers, virtual machines, namespaces, chroot isolation, or sandboxed app containers.

Runtime folders such as `sys/cache/`, `sys/installed_apps/`, and the user file root are normal project folders used by the shell.

## Imported Apps

Imported apps are Python modules. Python modules can execute Python code. Only load apps from sources you trust.
