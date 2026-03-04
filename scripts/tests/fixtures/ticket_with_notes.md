T20260219.0042 - Outlook crashes when opening large attachments

Company
Acme Corp

Location
Main Office

Contact
Sarah Johnson
sarah.johnson@acmecorp.com
555-123-4567

Priority
P3 - Medium

Description
User reports Outlook crashes immediately when attempting to open emails with attachments over 10MB.
Issue started after Windows update last Friday.
User needs to access a critical contract PDF sent by vendor.

Ticket Note | 2026-02-19 09:15 | Tech A
Initial triage: Confirmed issue reproduces with test attachment.
Checked Event Viewer - found AppCrash event for OUTLOOK.EXE.
Faulting module: olmapi32.dll

Ticket Note | 2026-02-19 10:30 | Tech A
Ran Office repair from Control Panel - completed successfully.
Issue persists after repair.
Gathering additional logs with SaRA tool.

Ticket Note | 2026-02-19 14:45 | Tech B
Reviewed SaRA results - detected corrupted Outlook profile.
Created new Outlook profile and migrated settings.
User confirmed issue resolved with new profile.
Closing ticket.

Attachment | 2026-02-19 09:20
Name
EventViewer_AppCrash.png
File Name / URL
https://storage.example.com/attachments/12345.png

Status
Resolved

Created
2026-02-19 08:45
