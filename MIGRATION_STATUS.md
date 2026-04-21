# Migration Status Dashboard
_Last updated: 2026-04-21 11:57:37_

## Scoreboard

| Metric | Value |
|--------|-------|
| Total Jobs | 9 |
| Migrated | 9 / 9 (100%) |
| QC Passed | 8 / 9 (89%) |
| QC Failed | 0 |
| Pipeline Runs | 17 |
| Current Job | `UFT.Prepare.AllSetup.RepView` |
| Latest Pipeline | `11225066` ❌ failed |

**Progress:** `████████████████████` 100% migrated  
**QC:** `█████████████████░░░` 89% QC passed

### Legend
| Badge | Meaning |
|-------|---------|
| 🟢 qc-pass | Migrated and QC confirmed equivalent |
| 🔴 qc-fail | Migrated but QC found a mismatch |
| 🟡 qc-blocked | QC could not run (infra/auth blocker) |
| 🔵 migrated | YAML pushed, QC not yet run |
| ⚪ pending | Not yet migrated |

---
## Pipeline Tree — Migration Progress

```

```

---
## Run Log

### Pipeline `11225066` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ failed | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.UFTSetup.PreFlight` | ✅ success | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Prepare.AllSetup.RepView`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11224469` — ✅ SUCCESS

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ✅ success | 0 | 7 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ✅ success | 0 | 17 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ✅ success | 298 | 106 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ✅ success | 2 | 51 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.UFTSetup.PreFlight` | ✅ success | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.WebAddin` | ✅ success | 0 | 16 | ⚪ | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ canceled | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

---

### Pipeline `11223617` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ✅ success | 0 | 7 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ✅ success | 0 | 17 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ✅ success | 338 | 106 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ✅ success | 2 | 51 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ failed | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.UFTSetup.PreFlight` | ✅ success | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.WebAddin` | ✅ success | 0 | 16 | ⚪ | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Prepare.AllSetup.UFTSetup`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11221983` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ✅ success | 0 | 7 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ✅ success | 0 | 17 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ failed | 2 | 82 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ failed | 2 | 46 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ failed | 2 | 331 | 🟡 | — |
| `UFT.Prepare.AllSetup.UFTSetup.PreFlight` | ✅ success | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.WebAddin` | ✅ success | 0 | 16 | ⚪ | — |
| `UFT.Setup.ALMAndBTP` | ❌ failed | 1 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Prepare.AllSetup.UFTSetup`**: _No QC report yet — run `/qc-job` for this job._
- **`UFT.Prepare.AllSetup.QCPlugin`**: _No QC report yet — run `/qc-job` for this job._
- **`UFT.Prepare.AllSetup.RepView`**: _No QC report yet — run `/qc-job` for this job._
- **`UFT.Setup.ALMAndBTP`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11178131` — ✅ SUCCESS

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ❌ canceled | 204 | 43 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ canceled | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

---

### Pipeline `11177878` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ failed | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ✅ success | 0 | 7 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ✅ success | 0 | 17 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ✅ success | 0 | 106 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ✅ success | 0 | 51 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ failed | 4 | 513 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ✅ success | 0 | 16 | ⚪ | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-qcplugin-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-repview-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-uftsetup-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Prepare.AllSetup.UFTSetup`**: _No QC report yet — run `/qc-job` for this job._
- **`UFT.Create.MLU`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11177572` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ failed | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-qcplugin-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-repview-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-uftsetup-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Create.MLU`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11177384` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ failed | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-qcplugin-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-repview-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-uftsetup-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Create.MLU`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11177222` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ failed | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-qcplugin-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-repview-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `fast-resume-mlusetup-uftsetup-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Create.MLU`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11176868` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ❌ failed | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`fast-resume-setuputils-bootstrap`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11176458` — ✅ SUCCESS

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ✅ success | 0 | 98 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ✅ success | 0 | 43 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ canceled | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

---

### Pipeline `11172142` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ✅ success | 0 | 7 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ✅ success | 0 | 17 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ✅ success | 0 | 106 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ✅ success | 0 | 51 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ failed | 1 | 333 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ✅ success | 0 | 16 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ✅ success | 0 | 98 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ✅ success | 0 | 43 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ✅ success | 0 | 430 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Prepare.AllSetup.UFTSetup`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11172125` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ❌ failed | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`fast-resume-setuputils-bootstrap`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11172068` — ✅ SUCCESS

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ canceled | 1 | 296 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ canceled | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

---

### Pipeline `11087051` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ✅ success | 0 | 98 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ✅ success | 0 | 43 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ failed | 0 | 0 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`UFT.Prepare.MLUSetup.UFTSetup`**: _No QC report yet — run `/qc-job` for this job._

---

### Pipeline `11086416` — ✅ SUCCESS

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ canceled | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ✅ success | 0 | 98 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ✅ success | 0 | 43 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ canceled | 0 | 0 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ✅ success | 0 | 3 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ canceled | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

---

### Pipeline `11086255` — ❌ FAILED

| Job | Status | Errors | Warnings | QC | Fix |
|-----|--------|--------|----------|----|-----|
| `INFRA.Net.Use` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.BuildNumber.Creator` | ✅ success | 0 | 0 | 🟢 | — |
| `UFT.Create.MLU` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Create.Setups.Wix.BuildSetup` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Create.Setups.Wix.CreatePFTW` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Attribute` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.CompanyName` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Copyrights` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Generic.ChangeBinFiles.Version` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.ExtAccTool` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.NetExtensibility` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.QCPlugin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.RepView` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.AllSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟡 | — |
| `UFT.Prepare.AllSetup.WebAddin` | ❌ skipped | 0 | 0 | ⚪ | — |
| `UFT.Prepare.MLUSetup.QCPlugin` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.RepView` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Prepare.MLUSetup.UFTSetup` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Setup.ALMAndBTP` | ❌ skipped | 0 | 0 | 🟢 | — |
| `UFT.Setup.Finalize` | ❌ skipped | 0 | 0 | ⚪ | — |
| `fast-resume-setuputils-bootstrap` | ❌ failed | 0 | 0 | ⚪ | — |
| `uft-build-compute-version` | ✅ success | 0 | 0 | ⚪ | — |
| `uft-build-env-setup` | ✅ success | 0 | 0 | ⚪ | — |

**Failed jobs — recommended fixes:**

- **`fast-resume-setuputils-bootstrap`**: _No QC report yet — run `/qc-job` for this job._
