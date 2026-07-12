# URL Shortener — PRD

## Overview

A web service that turns long URLs into short links and redirects visitors from the short link to the original URL.

## 1. Shortening

1.1. The service must accept a long URL and return a unique short link.

1.2. The same long URL submitted twice must return the same short link.

1.3. Short links must be as short as practical while remaining unique.

## 2. Redirection

2.1. Visiting a short link must redirect to its original long URL.

2.2. Visiting an unknown short link must return a not-found response.

## 3. API

3.1. The service must expose an HTTP endpoint to create a short link from a long URL.

3.2. The service must expose an HTTP endpoint that redirects a short link to its long URL.
