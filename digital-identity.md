# Digital Identity — Security Key & Authentication Reference
**Author:** Joseph C Thomas (JCT)
**Purpose:** Reference notes on how Windows Hello and Google Titan security keys work, and how to configure RoboForm to use a Titan key as 2FA (not a password replacement). Companion to `digital-identity-protection-checklist.md`, which tracks the action items — this file captures the underlying explanations.
**Version:** 1.4
**Version description:** Corrected an earlier error — RoboForm's Identity feature does not store document images, only text fields. Added a "Google Photos Locked Folder" section as the actual home for ID document photos, with the reasoning for why it's a reasonably secure choice.

---

## Windows Hello

Windows Hello is Windows' built-in biometric/PIN sign-in system — lets you log into your PC (and authenticate in apps/browsers that support it) using face, fingerprint, or a PIN instead of your full account password.

- **Face/fingerprint** use dedicated secure hardware (IR camera or fingerprint reader) and store biometric data locally, encrypted, tied to that specific device — never sent to Microsoft or usable to reconstruct your face/print.
- **PIN** is device-specific too, not synced or usable elsewhere — a stolen PIN only works on that one machine.
- Built on the same underlying tech as passkeys/FIDO2, so many websites and apps can use Windows Hello for passwordless sign-in.
- Requires compatible hardware (IR camera for face, capacitive reader for fingerprint) — configured under Settings → Accounts → Sign-in options.

---

## Google Titan Security Key

A physical USB/NFC/Bluetooth hardware token for phishing-resistant two-factor (or passwordless) authentication, built on FIDO2/WebAuthn and U2F standards.

**How it works:**

1. **Key pair generation, on-device.** When registering the key with a service, the key's secure element chip generates a unique public/private keypair *for that specific site*. The private key never leaves the hardware — not extractable, not backed up, not synced.
2. **Site gets the public key.** The service stores the public key against the account and issues a "challenge" on each login attempt.
3. **Login = signing a challenge.** The site sends a cryptographic challenge to the browser; the key signs it with the private key (after a tap/touch proving physical presence); the browser sends the signed response back. The server verifies it with the stored public key. Nothing secret crosses the wire.
4. **Origin binding is the phishing defense.** The signature is cryptographically bound to the requesting site's actual domain. A fake/lookalike site simply can't get a valid signature for the real account — unlike a password or SMS/TOTP code, which can be typed into a phishing site.
5. **Physical presence check.** The tap/touch proves a human is physically present, not just that malware has access to a stored credential.

**Form factors:** USB-A/USB-C + NFC (plug in or tap to phone), or Bluetooth (for devices without USB-C/NFC).

**Why stronger than SMS/authenticator codes:** those are "what you know/receive" — phishable (typed into a fake site) or interceptable (SIM swap for SMS). A security key's response is unphishable because the browser checks the origin matches before it will even ask the key to sign.

---

## Role of the PIN

**On the Titan key itself (FIDO2 PIN):** newer Titan keys support setting a PIN directly on the key, enabling **user verification (UV)**, distinct from the tap/touch **user presence** check.

- User presence (tap) proves *something* touched the key — could be anyone holding it.
- User verification (PIN) proves *you specifically* are using it. Entered into the browser/OS prompt, relayed to the key to unlock the signing operation.
- Verified **locally on the key's chip** — never sent to the website. The key locks itself after too many wrong attempts (protects a lost/stolen key from brute-force).
- Some services (especially passwordless/passkey sign-ins that *replace* the password entirely) require UV, so a PIN-less key can't be used for those flows.

**On Windows Hello:** same underlying idea — the PIN unlocks a private key held in the PC's TPM, verified locally, never transmitted or synced. Identical "local unlock, proves it's you" role as the FIDO2 PIN above.

In both cases, the PIN is a **local unlock mechanism** for a private key already living in tamper-resistant hardware — not a network-facing secret like a password. That's why a stolen PIN alone is useless without also having physical possession of the specific device/key.

---

## RoboForm — Configuring a Titan Key as 2FA (not a passkey/password replacement)

RoboForm splits security into two separate sections under **Log In & Security**:

- **Passwordless Unlock** — lets the key (or biometrics) *replace* the master password entirely.
- **Two-Factor Authentication** — adds the key as an *extra* requirement on top of the master password.

"Passkeys" is just the underlying technology label (FIDO2/WebAuthn) RoboForm uses for both categories — which bucket a key lands in depends entirely on which section it's added from.

### Setup steps (adds the key as 2FA)

1. Click the RoboForm extension icon → **⋮** (three dots, top right) → **Settings**.
2. Go to **Log In & Security** → **Two-factor authentication**.
3. Click **Add 2FA Method**.
4. Select **Passkeys**.
5. When asked where to save the passkey, choose **Security Key**, then **Next**.
6. Confirm you want to set up the key to sign in to RoboForm.
7. Confirm you're okay letting RoboForm see the key's make/model.
8. Insert/tap the Titan key when prompted — Windows shows its own WebAuthn dialog asking for the Windows PIN (or Hello face/fingerprint), then asks you to touch the key itself. Enter the PIN and confirm.

Only newer hardware keys that support passkeys work with RoboForm (Google Titan and YubiKey Security Key C NFC confirmed compatible).

### Confirming it's 2FA, not passwordless unlock

1. Go back to **Log In & Security**.
2. Check **Passwordless Unlock** — the Titan key should **not** be listed/enabled there. Remove it if it is.
3. Confirm it **is** listed under **Two-Factor Authentication**.
4. Test by logging out and back in — should prompt for master password first, *then* the security key tap, not the key alone.

**Also register a backup key.** If the primary key is lost and it's the only passkey/2FA key registered, account recovery gets difficult. Register a second key (e.g., the shared/backup Titan from `digital-identity-protection-checklist.md`) at the same time rather than after being locked out.

---

## Shared 4-Digit PIN Selection (Joseph & Robin)

A 4-digit PIN has only 10,000 possible combinations, and PIN-guessing has been studied extensively — a well-known 2012 analysis of leaked PIN datasets found the top 20 PINs cover roughly 27% of all real-world PINs in use.

**Absolutely avoid — statistically the first things guessed, not just "weak":**
- Any date: birthdays, anniversaries, "MMDD" patterns — dominate the guessable set because they're common and often derivable from social media/public records
- Repeats and sequences: 1111, 1234, 4321, 0000
- Keypad shapes: 2580 (straight down the middle), 1470, 0852 — common because they're easy to type
- Last 4 of a phone number, SSN, or address digits

**Best technique: generate it randomly and store it, don't hand-pick it.**
Human-chosen "clever" PINs still cluster into predictable patterns (attackers model this). The strongest move within a 4-digit space is true randomness:
- Use RoboForm's password generator to produce a random 4-digit string, or roll dice (e.g., two 10-sided dice, or a d6 + d10 combo, twice).
- Write it down and store it in the safe — same offline-hardcopy pattern already used for backup codes and hardware key serials (see the Offline Hardcopy Vault section in `digital-identity-protection-checklist.md`).
- Memorize it through repetition (typing it daily) rather than deriving it from something meaningful — meaning is exactly what makes PINs guessable.

**Caveat:** this matters proportional to how guess-attempts are limited on whatever the PIN protects. If it's hardware-lockout-protected (a phone, a bank card), avoiding the top-20 common PINs already captures most of the real-world benefit. If it's protecting something with unlimited offline guessing, true randomness is the only thing that helps at 4 digits — worth checking whether that context should use a longer PIN instead, if supported.

---

## What NOT to Store in RoboForm (or any app)

A password manager is a poor fit for anything meant to be the *escape hatch* if the manager itself fails — storing it there collapses the fallback back into the same single point of failure the rest of this checklist is designed to eliminate.

**Never store in RoboForm (or any app) — keep fully offline, on paper/metal, in the safe:**

- **Crypto wallet seed phrases / private keys.** These are *bearer secrets* — whoever has the string has the funds, permanently, with no reset and no recourse. Password manager breaches (e.g., LastPass 2022) have directly led to crypto theft specifically because people stored seed phrases in them. Paper or metal backup, offline, always.
- **RoboForm's own master password.** The vault can't store the key that unlocks the vault.
- **RoboForm's own account-recovery codes / Emergency Access details.** Same circular-lockout logic — if RoboForm itself is ever inaccessible, the recovery path can't live inside the thing that's down.
- **The household codeword** (Phase 3 of `digital-identity-protection-checklist.md`). Its entire value is being an out-of-band channel a compromised digital account can't touch. Storing it in RoboForm defeats that.
- **The safe's combination or key location.** The safe is the physical fallback for the digital vault — it shouldn't depend on the digital vault to be found.

**Okay to store in RoboForm, but worth a second thought:**

- **SSN, passport numbers, other static/non-rotatable IDs.** RoboForm's encryption is solid, but unlike a password these can't be reset if ever exposed — consider a specially-flagged note or offline-only storage rather than mixing them in with rotatable logins.
- **Hardware key serial numbers** — fine as reference text, just never the key's own PIN.

**Underlying rule:** anything meant to be the escape hatch if the primary system fails has to live in a genuinely separate failure domain. If it's inside RoboForm, it's not independent of RoboForm being compromised or unavailable — it's the same point of failure wearing a different hat.

---

## Google Photos Locked Folder (for ID document photos)

**Correction:** earlier guidance in this project claimed RoboForm's Identity feature could store passport/driver's license *images*. That's wrong — RoboForm's Identity only holds structured text fields (number, dates), with no attachment/image support at all. Passport/DL numbers and expiration dates still belong there; the actual photo needs a different home.

**Google Photos' Locked Folder** is that home. It's a separate area within Google Photos, gated by an additional local check beyond the account login itself (device passcode, Face ID, or fingerprint), with these properties:

- **Excluded from the normal surfaces:** not shown in the main timeline, not indexed by search, not surfaced in "Memories," not visible to family/partner library sharing.
- **Can't be link-shared while inside it.** A photo has to be deliberately moved *out* of Locked Folder before any share link can be generated — so there's no accidental-exposure path via a stray shareable link.
- **Cross-device backup** (Android, iOS, and web) — a photo saved in Locked Folder on one device is accessible on others, protected the same way. Earlier versions of this feature were device-local only; that's no longer the case.
- **Inherits the Google Account's own hardening** — hardware-key-only 2FA, no phone-based recovery fallback — since it's still gated by the same account sign-in underneath the extra local check.

**Where to reference it:** don't store a link to specific Locked Folder photos anywhere (there isn't one to store, per above) — just a plain locator note in RoboForm, e.g. "ID photos: Google Photos → Locked Folder." That's not a secret, just a reminder of where to look.
