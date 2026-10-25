# Who Built My Home account separation

The user designated `whobuiltmyhome@gmail.com` as this project's Google account
on October 12, 2026. Use it for Search Console and Google Analytics ownership
and administration. Do not choose a personal Google account merely because it
is already signed in or is the browser's default.

Before a future external-service registration, confirm the intended account
with the user unless the current request already explicitly identifies it.
Check the active account displayed by the service before submitting account
creation, ownership verification, or access changes. Existing authorization
for the named project account does not need to be requested again.

Search Console and Google Analytics have separate properties and permissions.
Correct ownership/access on the existing property when possible to preserve
history. Do not create a replacement Analytics property or change its measurement
ID merely because the project account cannot yet see the existing stream.
See `docs/analytics.md` for the activation gate and project-account status.

Use secure browser sign-in for credentials. Never request passwords or one-time
codes in chat, or place credentials in repository files.

The user reaffirmed account separation on October 25, 2026. Keep source changes,
pull requests, and GitHub Pages publication in the dedicated GitHub repository
`whobuiltmyhome/whobuiltmyhome-site`, using the `whobuiltmyhome` identity. Do not
move or fork this project into a personal GitHub account for routine updates.
Verify the connected GitHub identity before writes when that identity is unknown.
