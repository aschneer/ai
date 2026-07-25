# Link-in-Bio Page Builder — PRD

A hosted service where a user builds a single public page of links and shares one short URL to it.

## 1. Accounts

**1.1.** A visitor can create an account with an email address and password.

**1.2.** A user can sign in and out.

**1.3.** Each account owns exactly one public page.

## 2. Page editing

**2.1.** A user can add a link, consisting of a destination URL and a display label.

**2.2.** A user can edit the label or destination of an existing link.

**2.3.** A user can delete a link.

**2.4.** A user can reorder their links, and the public page reflects that order.

**2.5.** A user chooses a subdomain for their page, unique across all accounts.

- **2.5.1.** A subdomain already in use is rejected with an explanatory message.

## 3. Public page

**3.1.** The page is reachable without authentication at the user's chosen subdomain.

**3.2.** The page renders the user's links in their chosen order.

**3.3.** The page is legible on a phone-sized screen.

**3.4.** A page for a subdomain that does not exist returns a not-found response.

## 4. Analytics

**4.1.** A user can see the total number of clicks on each of their links.

**4.2.** Click counts are visible to the owning user only.
