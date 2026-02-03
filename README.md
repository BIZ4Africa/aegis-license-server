# AEGIS – License Control Framework (Server)

AEGIS is a proprietary licensing and enforcement framework developed by **Business Solutions For Africa (BIZ4A)**.
It is designed to protect high-value Odoo modules that embed significant intellectual property, regulatory logic,
or domain-specific business intelligence.

This repository contains:
- the **AEGIS License Server** (license authority)
- the **official project specifications** used as contractual and technical references

AEGIS is intentionally designed **without relying on security by obscurity**.  
Instead, it combines a strong legal foundation with robust, pragmatic technical enforcement.

---

## 1. What is AEGIS?

AEGIS (Advanced Enforcement & Governance for Intellectual Software) is a dual-component system:

1. **License Server**
   - Issues and signs license keys
   - Manages license lifecycle (perpetual, subscription, demo)
   - Optionally exposes validation endpoints

2. **Odoo Client (separate repository)**
   - Embedded into proprietary Odoo modules
   - Verifies license signatures (offline-first)
   - Enforces license rules at install time and runtime

This repository focuses on **component #1**.

---

## 2. Licensing Model

All AEGIS-protected modules are distributed under:

- **Odoo Proprietary License v1 (OPL-1)**

OPL-1 is extended by a **BIZ4A Commercial License Addendum**, which defines:
- license duration
- version eligibility
- demo and trial rules
- maintenance and upgrade conditions

The addendum is documented in the project specifications.

---

## 3. Key Design Principles

- Proprietary, commercial licensing
- Offline-first validation (mandatory)
- Optional online validation
- Structural enforcement (dependency-based)
- Odoo.sh and on-premise compatibility
- Minimal friction for legitimate customers

AEGIS does **not** attempt DRM-level protection.

---

## 4. Repository Structure

```
aegis-license-server/
├─ README.md
├─ LICENSE
├─ docs/
│  ├─ specs/        # Functional & technical specifications
│  ├─ adr/          # Architecture Decision Records
│  └─ diagrams/     # Reference diagrams (Mermaid)
├─ server/          # License server implementation
├─ deploy/          # Deployment assets (Docker, etc.)
└─ .github/         # CI, workflows, issue templates
```

---

## 5. Specifications

All authoritative project specifications are located in:

```
docs/specs/
```

They include:
- objectives and scope
- functional and non-functional requirements
- licensing model (OPL-1 + addendum)
- architecture and trust model
- license payload schema
- acceptance criteria
- threat model

These documents are part of the **formal deliverables** of the AEGIS project.

---

## 6. Target Environments

- Odoo.sh
- On-premise Odoo deployments
- Offline or low-connectivity environments

No system-level dependencies are required.

---

## 7. Security Model (Summary)

- Private signing keys are stored **only** on the server
- Public verification keys are embedded in the Odoo client
- License payloads are immutable and signed
- Tampering invalidates the license

---

## 8. Project Status

This repository is under active development.
Breaking changes are tracked via:
- GitHub Issues
- ADRs
- Tagged releases

---

## 9. Related Repositories

- **AEGIS Odoo Client** (license enforcement module)
- Proprietary BIZ4A Odoo modules depending on AEGIS

Access is restricted according to commercial agreements.

---

## 10. Maintainer

**Business Solutions For Africa (BIZ4A)**  
Digital Transformation & Enterprise Solutions

© BIZ4A – All rights reserved.
