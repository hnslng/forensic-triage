# Forensic safety

Before analysis, the operator must establish authorization and identify the physical medium by transport, capacity, model, and serial number. Device names such as `/dev/sdb` are ephemeral and must never be assumed.

The implemented sequence is:

1. Resolve the supplied `/dev` path.
2. Require a whole disk with USB transport.
3. Refuse the explicit `/dev/sda` system-disk sentinel.
4. Recursively reject any mountpoint on the device or its partitions.
5. Set the whole disk read-only.
6. Verify kernel read-only state equals `1`.
7. Run `mmls` and `fsstat`.
8. In fast mode, mount only with `ro,nosuid,nodev,noexec`, verify the mount is `ro`, collect metadata, and unmount in a `finally` cleanup path.
9. In TSK mode, use mount-free `fls -u` instead.

Linux documents that a filesystem mounted `ro` may still perform filesystem-specific writes in some circumstances. The scanner therefore sets and verifies the block device itself read-only before mounting. The current software guard is still defense in depth, not a forensic write blocker. Production use requires a validated hardware write blocker, documented device handling, tool validation, synchronized time, and an organizational chain-of-custody procedure.

No credential, private key, genuine case data, or result directory belongs in Git.
