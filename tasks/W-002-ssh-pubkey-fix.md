# W-002 — Fix SSH public-key auth for the Pi session

**Owner:** Workstation Claude (run locally on the Workstation, 192.168.110.11)
**Direction:** Workstation management — bootstraps Phase A of the Pi→Workstation migration.

---

## Goal

Allow the **Pi** Claude session (user `pi` on 192.168.110.225) to SSH into this
Workstation as **`dan-linux`** using its ed25519 key, **without a password**.

Right now the Pi offers its key but this Workstation rejects it
(`Permission denied (publickey,password)`), even after the user ran `ssh-copy-id`
twice. So the key is either not in the right `authorized_keys`, or — more likely —
sshd is refusing it because of permissions or config. Your job is to find which and
fix it.

## The Pi's public key (must end up authorized for `dan-linux`)

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBHlUOM4rW6nJKcHP6uP2YOsN370z076c+ZWkS4EBP1i
```

Its fingerprint (what you should see sshd offered in the auth log):
`SHA256:Aev/pp9mONPnJGzsaqJReNr/kt/YCROdFPY8IMsrHTA`

## Diagnose (run on the Workstation)

1. Confirm the key is present and in the right file:
   ```
   grep -n "EBP1i" ~/.ssh/authorized_keys
   ```
   If missing, append the key above to `~/.ssh/authorized_keys`.

2. Check permissions — sshd silently refuses keys if any are too open:
   ```
   ls -ld ~ ~/.ssh ; ls -l ~/.ssh/authorized_keys
   ```
   Required: home `~` must NOT be group/other-writable; `~/.ssh` = `700`;
   `~/.ssh/authorized_keys` = `600`; both owned by `dan-linux`.

3. Check sshd config for anything that would block it:
   ```
   sudo sshd -T | grep -Ei 'pubkeyauthentication|authorizedkeysfile'
   ```
   Expect `pubkeyauthentication yes` and the default
   `authorizedkeysfile .ssh/authorized_keys .ssh/authorized_keys2`.
   Also check `/etc/ssh/sshd_config.d/*` for overrides (e.g. a cloud-init drop-in
   setting `PubkeyAuthentication no` or a `Match` block).

4. If still stuck, watch the live auth log while the Pi retries:
   ```
   sudo journalctl -u ssh -f
   ```
   (Tell the user to ping you / or just inspect the most recent
   `Authentication refused` line — it names the exact reason, e.g.
   "bad ownership or modes for directory".)

## Fix

Apply whatever the diagnosis found. The usual one-shot fix:
```
install -d -m700 ~/.ssh
grep -q "EBP1i" ~/.ssh/authorized_keys || \
  echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBHlUOM4rW6nJKcHP6uP2YOsN370z076c+ZWkS4EBP1i' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod g-w,o-w ~
```
If an sshd drop-in disabled pubkey auth, re-enable it and
`sudo systemctl reload ssh`.

## Acceptance criteria

- [ ] `~/.ssh/authorized_keys` (owned by `dan-linux`, mode 600) contains the
      `...EBP1i` key.
- [ ] `~` is not group/other-writable; `~/.ssh` is mode 700.
- [ ] `sudo sshd -T | grep pubkeyauthentication` → `pubkeyauthentication yes`.
- [ ] From **another machine on the LAN** (or note in the result) a key-based login
      as `dan-linux` succeeds with no password. The real test is the Pi running
      `ssh -o BatchMode=yes dan-linux@192.168.110.11 'hostname'` — but you can't run
      that from here, so just record what you changed and confirm the three boxes
      above; the Pi will do the final BatchMode test.

## Report back

1. In `tasks/INDEX.md`, mark **W-002** Done with a one-line result naming the actual
   root cause (e.g. "home was group-writable" / "key was missing" / "cloud-init
   drop-in disabled pubkey").
2. Commit `W-002: fix SSH pubkey auth for Pi session` and push.
