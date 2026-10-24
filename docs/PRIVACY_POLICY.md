# Mayomix Privacy Policy

**Last updated:** 24-10-2026  
**Contact:** bhatmmr@gmail.com 
**Service operator:** Ammar

This Privacy Policy explains how Mayomix ("Mayomix", "we", "us", or "our") handles information when you use the Mayomix website, application, and API (the "Service"). It is written for the current features of the Mayomix backend and must be updated if the Service or its infrastructure changes.

Mayomix is currently a music-review and social service. Users can create profiles, publish album reviews and music-taste lists, search for other users, send connection requests, and view activity from accepted connections.

## 1. Information we handle

### Information you provide

Depending on how you use the Service, we may process:

- **Account details:** name, username, email address, and password.
- **Profile details:** biography, profile-picture URL, and favourite genres.
- **Music-taste details:** music identifiers, categories, rankings, and whether an entry is marked as liked.
- **Reviews:** review text, rating, album/music identifier, and creation or update dates.
- **Social information:** connection requests, whether a request has been accepted, and connection dates.
- **Messages sent to us:** information you include if you contact us using the contact details we publish.

Mayomix currently accepts a profile-picture link (URL); the backend does not currently provide an image-upload service.

### Authentication and security information

When you register, Mayomix stores a password hash generated using Argon2 through its password-hashing library. The password is not intended to be stored as plain text. When you sign in, the Service issues a bearer access token (JWT) that expires according to the configured token lifetime.

Do not share your access token with other people. The current backend does not implement email verification, password-reset email, or refresh-token functionality.

### Information created through use

The Service records account creation dates and dates associated with reviews and accepted connections. It also stores cached music metadata so it can serve album information without always fetching it again.

### Information collected automatically

The current application code does not implement advertising trackers or an analytics product. However, the API host, database host, network infrastructure, or other providers used to operate the Service may automatically process technical information such as IP address, request time, user-agent, error, and security logs. The exact information and retention period depend on the providers and deployment configuration. We will update this policy if we add analytics, tracking technologies, or other automatic collection.

## 2. How information is used

We use information as reasonably necessary to:

- create and manage accounts and authenticate users;
- display profiles, favourite genres, taste lists, reviews, ratings, and social activity;
- support username search, connection requests, and activity feeds;
- retrieve music information and album artwork from external services;
- cache album metadata and maintain the Service;
- protect the Service, investigate misuse, troubleshoot errors, and maintain security; and
- respond to requests and meet applicable legal obligations.

We do not currently operate an advertising or behavioural-advertising feature in the backend.

## 3. What other users can see

MayoMix has public and social features. In the current backend:

- Public profile responses can include your name, username, biography, profile-picture URL, and favourite genres.
- Your taste lists can be retrieved by username.
- Your reviews can be retrieved by username, review identifier, or album identifier.
- Username search can return your name, username, profile-picture URL, and favourite genres.
- The activity feed is available to an authenticated user and includes reviews from that user and their accepted connections.
- Your email address is returned by the authenticated “my profile” endpoint; it is not included in the public profile response.
- Connection and pending-request details are available through authenticated connection endpoints.

Do not include information in a public profile, taste list, or review that you do not want other users to see. A profile-picture URL may point to a third-party host, which may process requests when the image is loaded.

## 4. External services

Mayomix currently uses:

- **MusicBrainz** to search for and retrieve music metadata.
- **Cover Art Archive** to check for and link to album artwork.

When you search for music or request album details, relevant search terms or music identifiers are sent to these services. Album artwork is linked from the Cover Art Archive rather than uploaded to Mayomix by the backend. Those providers operate under their own terms and privacy practices. Review their policies before using their services.

The backend also depends on whichever hosting, database, networking, and file or image services are configured for the deployed version. Those providers may process information on our behalf. Their identities and applicable terms should be added here before public launch once the production setup is selected.

## 5. Legal bases and choices

We handle personal information for the purposes described in this policy and in accordance with applicable law. Depending on the law that applies, the relevant basis may include providing the Service you request, your consent, our legitimate operational and security needs where recognised by law, or compliance with legal obligations.

Where applicable law requires consent, we will seek it and provide a way to withdraw it. Withdrawing consent does not invalidate processing that took place before withdrawal, and it may mean that some features cannot be provided.

If India's Digital Personal Data Protection Act, 2023, or related rules apply to our processing, we will handle personal data in accordance with the provisions and obligations applicable at the relevant time. Legal requirements and commencement dates can change; this statement is not a claim that every statutory provision is already in force.

## 6. Retention and account deletion

We keep information for as long as needed to operate the Service, meet the purposes described here, resolve disputes, enforce our terms, and comply with legal obligations.

The current backend provides an account-deletion endpoint. When it succeeds, it deletes the account record, that user's reviews and taste entries, and connection records involving that user from the application database. It does not delete the shared cache of music metadata. Information may remain for a limited period in infrastructure logs or backups maintained by service providers, where applicable, and may be retained where required by law.

Deletion through the current endpoint is not an assurance that every copy in third-party systems, logs, or backups is immediately erased. If you need help with a privacy request, contact bhatmmr@gmail.com.

## 7. Security

MayoMix uses password hashing and token-based authentication, and applies access checks to protected account actions. No online service or method of storage can be guaranteed to be completely secure. You should use a unique password, protect your access token, and contact us if you believe your account has been compromised.

## 8. Children

The Service is not designed to knowingly collect personal data from children in circumstances where doing so would violate applicable law. If you believe a child has provided personal data inappropriately, contact bhatmmr@gmail.com so we can review the request and take appropriate action.

Before launch, the operator should decide and publish an age policy appropriate to the intended audience and applicable law.

## 9. Your privacy rights

Depending on your location and applicable law, you may have rights to request access to, correction of, or deletion of personal data, withdraw consent, raise a grievance, or make a complaint to the relevant authority.

You can edit certain profile information and delete your account using available Service features. For requests that those features do not support, contact bhatmmr@gmail.com. We may need to verify your identity before responding and will respond in accordance with applicable law.

If you are in India and the relevant provisions apply, you may also have rights and grievance mechanisms provided under Indian data-protection law.

## 10. International processing

MusicBrainz, Cover Art Archive, and the infrastructure providers used by the deployed Service may process information in countries other than your own. The locations involved depend on the providers and deployment configuration. We will update this section when production providers and relevant data locations are confirmed, and will comply with applicable transfer requirements.

## 11. Changes to this policy

We may update this Privacy Policy when the Service, our data practices, or applicable law changes. We will update the “Last updated” date and, where required, provide notice or obtain consent for material changes. The updated policy applies from its stated effective date, subject to applicable law.

## 12. Contact

For privacy questions, requests, or grievances, contact:

- **Service operator:** Ammar
- **Privacy contact email:** bhatmmr@gmail.com

