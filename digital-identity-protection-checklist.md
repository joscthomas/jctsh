# Digital Identity Protection Checklist
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step checklist for Joseph and Robin to close the single-point-of-failure risks described in the TIME article "How a Stranger Used One Text Message to Steal My Entire Digital Life" (July 2026).
**Version:** 1.2
**Version description:** Confirmed children are adults with independent Google accounts (recovery contacts unblocked); clarified offline hardcopy plan (safe now, travel/outside-contact copies under consideration); set a ~1-month target for hardware key setup now that Titans are on order.

---

## Phase 1 — Lock the Front Door (this week)

### Carrier (do for both lines)
- [X] Call carrier and add a port-out PIN / number lock (T-Mobile: "Account Takeover Protection," Verizon: "Number Lock," AT&T: "Extra Security PIN")
    - Enabled number lock on all lines (2026/07/08)
- [X] Confirm SIM swap requires in-person ID or the PIN, not just knowledge of SSN/DOB
  - Enabled SIM protection on all lines (2026/07/08)
- [X] Robin: same steps on her line/carrier

### Google Account (do for both)
- [X] Change Google Account PIN
- [ ] Delete security question
- [ ] Delete recovery phone number (Joseph and Robin) — once hardware keys are registered and confirmed working
- [ ] Order 3 Google Titan security keys (1 for Joseph, 1 for Robin, 1 shared backup for the safe)
- [ ] Register Joseph's Titan as a passkey on his Google Account
- [ ] Register Robin's Titan as a passkey on her Google Account
- [ ] Register the shared/backup Titan as a passkey on both accounts; store in the safe once done
- [ ] Set up Windows Hello as a passkey on Joseph's laptop *(under consideration, not yet decided)*
- [ ] Review "recent security activity" / connected devices, remove anything unrecognized or old
- [ ] Consider enrolling in Google Advanced Protection Program if either of you handles significant money

### Credit (do for both, now — not after an incident)
- [ ] Freeze credit at Equifax
- [ ] Freeze credit at Experian
- [ ] Freeze credit at TransUnion
- [ ] Freeze at ChexSystems
- [ ] Freeze at LexisNexis

---

## Phase 2 — Break the Single Point of Failure (this month)

### Dedicated recovery phone number (for non-Google accounts)
- [ ] Set up a second, low-profile phone number (Google Voice or second carrier line) — now scoped specifically to institutions that still require phone-based 2FA and don't support passkeys/hardware keys (e.g., banks, brokerages, the credit union), since Google's own recovery phone is being removed in favor of hardware keys
- [ ] If using Google Voice, set a recurring reminder to keep it active (3-month inactivity reclaim policy), or use a small autopay carrier line instead to avoid the upkeep

### Password manager (RoboForm)
- [X] RoboForm in use for password management (long-standing)
- [X] RoboForm 2FA enabled via Google Authenticator
- [ ] Add hardware-key 2FA to RoboForm once Titans arrive (confirmed supported: YubiKey Security Key C NFC / Google Titan)
- [ ] Confirm Robin has her own independent RoboForm login/vault access, not dependent on a shared password
- [ ] Evaluate RoboForm Emergency Access (grants a designated person access to credentials upon death or incapacitation) — decide who the designated contact should be
- [ ] Move to unique, generated passwords for bank, brokerage, crypto, and email accounts first if not already done

### Recovery contacts
- [ ] Set Google Account Recovery Contacts: Robin ↔ Joseph (each other)
- [ ] Add both children as recovery contacts (confirmed: both are adults, each with their own independent Google account)
- [ ] *(Under consideration, not yet implemented)* Shared codeword system with children for identity verification

### Offline hardcopy vault
- [ ] Generate Google 2-Step Verification backup codes for Joseph and Robin
- [ ] Record hardware key serial numbers
- [ ] Store offline hardcopy (backup codes, key serial numbers, account numbers, insurance policy numbers, IDs) in the safe — decided, current plan
- [ ] *(Under consideration)* Travel copy: a small, unlabeled duplicate carried separately from phone/hardware key while traveling (see Phase 5)
- [ ] *(Under consideration)* Outside-contact copy: a third duplicate held by someone outside the household — see "Outside-Contact Copy Pattern" note below

> **Outside-Contact Copy Pattern:** the safe protects against a lost phone or device; it does not protect against a household-level event — a house fire, a burglary, or both of you traveling together and losing the same bag. A third duplicate of the backup codes/serials, held by someone who lives elsewhere (e.g., one of the children, since both are independent adults), survives exactly that scenario. It doesn't need to be requested often — it just needs to exist for the rare case where both the safe copy and any travel copy are unreachable at once. Same logic as having Recovery Contacts in a different location from your own household.

### General
- [ ] Confirm neither of you can be fully locked out of money and communication by the loss of one single device or account (test/fire-drill)

---

## Phase 3 — Household Protocol

- [ ] Agree: never read a verification code to anyone who calls — hang up, call the number on the back of the card instead
- [ ] Agree: any request to move money gets a voice call to confirm, even if the text/app notification appears to come from each other
- [ ] Decide whether a shared verbal codeword is worth adding for ambiguous/urgent requests (Joseph ↔ Robin)
- [ ] *(Under consideration, not yet implemented)* Extend codeword system to children
- [ ] Walk through this checklist together so both of you know it exists and where it lives

---

## Phase 4 — Incident Response Plan (keep a copy of this accessible offline)

1. [ ] From another device, use a hardware security key to sign into Google, change the password, and revoke all active sessions immediately
2. [ ] Call carrier to lock/freeze the SIM before anything else
3. [ ] Call banks/brokerages/credit union using the number on the card/statement — never a number that contacted you
4. [ ] File a report at identitytheft.gov (FTC)
5. [ ] File a police report and get the report number
6. [ ] Document everything as you go: timestamps, amounts, reference numbers, names of who you spoke to

---

## Phase 5 — Travel Considerations

- [ ] Carry hardware keys separately (not both/all in the same bag) — Joseph's key on Joseph, Robin's key on Robin
- [ ] Leave the shared/backup Titan key at home; don't travel with all three keys at once
- [ ] Confirm at least one 2FA method traveling with you is independent of your phone (hardware key or laptop passkey)
- [ ] Check dual-SIM/eSIM setup keeps your home number active alongside any local SIM used abroad
- [ ] Call carrier before international travel to confirm the port-out lock isn't relaxed for roaming support scenarios
- [ ] Carry a travel copy of backup codes — small, unlabeled, kept separate from phone and hardware key
- [ ] Brief recovery contacts (Robin, children, any outside contact) on travel dates before departure
- [ ] Carry a non-digital payment fallback: physical card plus some cash
- [ ] Notify banks/credit union of travel dates

---

## Appendix A — Scenario Walkthroughs

**Scenario A — One phone stolen while traveling, other person unaffected.** Hardware key (carried separately from the phone) signs into Google directly on a borrowed device or the other person's phone; carrier port-out lock already blocks SIM swap; Find My Device locks the phone; physical cash/card cover immediate needs. Resolves in minutes without needing a recovery contact.

**Scenario B — Both phones lost/stolen together (bag theft, hotel burglary).** If hardware keys were carried on-person rather than in the stolen bag, each person signs back in independently with their own key. If a key is lost too, fall back to a Recovery Contact: reach them by any available channel, confirm identity with the household codeword, have them relay the Google-generated verification code. Pull account details from the offline vault copy that stayed home or with a trusted contact — not the one that traveled.

**Scenario C — Spoofed "fraud alert" call while traveling.** Hang up on any inbound call asking to read back a code or confirm SSN/DOB, regardless of how convincing it looks. Call the number on the back of the card independently. With no recovery phone left on the Google account and hardware keys required for recovery, the "read me the code" trick has nothing to exploit. If the scammer pivots to the other spouse with a fake payment request, the household protocol (voice confirmation, codeword if needed) blocks it.

---

## Accounts Without 2FA — Compensating Controls (e.g., Credit Union)

- [ ] Ask directly whether 2FA/MFA exists but isn't obvious (may live in the mobile app rather than the website)
- [ ] Ask about setting a verbal password/passphrase required for any phone-based account changes or discussions
- [ ] Turn on every available alert: new-device login, transaction/withdrawal alerts, failed-login alerts
- [ ] Ask if they offer a callback/manual hold requirement for transfers above a set amount
- [ ] Ensure the account password is long, unique, and generated — stored in RoboForm, never reused
- [ ] Limit balance held there long-term; sweep excess to an account with real 2FA
- [ ] Reassess whether this should remain a primary account long-term if 2FA is never added

---

## Open Items to Fill In

- [ ] List specific banks/brokerages/payment apps in use, so carrier- and institution-specific steps can be added
- [X] Confirm current password manager / 2FA setup — RoboForm confirmed in use, hardware-key upgrade pending key delivery
- [X] Confirm children's ages and Google account independence — both are adults with their own independent Google accounts
- [ ] Decide on travel-copy and outside-contact-copy adoption for backup codes/serials (safe copy already decided)
- [ ] Decide who holds RoboForm Emergency Access designee status, if enabled
- [ ] Target: complete hardware key setup (order → registration on both accounts + RoboForm) within ~1 month (by 2026-08-08), since Titans are already on order
- [ ] Set a review date to revisit this checklist (recommend: 6 months, or at hardware key setup completion, whichever comes first)
