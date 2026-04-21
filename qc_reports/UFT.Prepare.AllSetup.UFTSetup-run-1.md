QC_STATUS: BLOCKED
Pipeline: 11172142 (branch: fast-test-setup-20260417, date: 2026-04-20)
Job: UFT.Prepare.AllSetup.UFTSetup
Jenkins Reference: fetch_xml/build_logs/UFT.Prepare.UFT.Setup.log

## Root Cause
INFRASTRUCTURE BLOCKER — not a YAML defect.

Error from log:
  SCM_MSG_ERROR: Unhandled Exception in CreateInstallationFiles!;Exception=There is not enough space on the disk.

The MSBuild target PrepareUFTSetup_IHP2 on create_msi.proj ran correctly but exceeded disk capacity on the runner when assembling installer staging files.

## Evidence
- GitLab log: pipeline_logs/p11172142_UFT.Prepare.AllSetup.UFTSetup.log
- MSBuild target: PrepareUFTSetup_IHP2 on build\create_msi.proj — correct (matches Jenkins)
- Jenkins reference: "build\create_msi.proj | PrepareUFTSetup_IHP2 — SUCCESS"
- YAML is correct; same target, same project file, same parameters
- Failure occurred ~2.5 minutes into the PrepareUFTSetup_IHP2 target execution
- E=1: "There is not enough space on the disk"

## Context
- Earlier in same pipeline, UFT.Prepare.MLUSetup.UFTSetup ran for ~25 min and assembled hundreds of MB of artifacts into the runner workspace.
- UFT.Prepare.AllSetup.UFTSetup assembles the full MSI staging tree (larger than MLU), which requires multiple GB of temporary disk space.
- Runner: EC2 instance KK9B08ihI on EC2AMAZ-3H281CR

## What Is Needed
1. Free disk space on runner KK9B08ihI (EC2AMAZ-3H281CR): clean up old build workspace directories (C:\GitLab-Runner\builds\)
2. OR use a runner with more disk capacity
3. Re-run the pipeline — the YAML requires no changes

## Next Step After Resolution
Re-run pipeline after runner disk is freed. This job is expected to pass; YAML is verified correct.
