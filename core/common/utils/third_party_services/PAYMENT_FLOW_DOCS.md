## 📄 Mobile Payment Flow Documentation

### Overview

This document describes the payment flow for mobile apps in the Cluster platform. Payments are initiated via the backend (Paystack or Flutterwave), and completed via a WebView or Chrome Custom Tab in the Flutter mobile app. Upon completion, the user is redirected back to the app using deep linking.

---

### 🔁 High-Level Flow

1. **Flutter app** requests payment from the backend.
2. **Backend** calls the PSP (Paystack/Flutterwave) to initialize the payment.
3. **Backend** returns the `authorization_url` and `reference` to the app.
4. **App** opens the `authorization_url` in a WebView or Chrome Custom Tab.
5. **User completes payment** on hosted checkout UI.
6. **User is redirected** to a deep link or confirmation page with a redirect button.
7. **App catches deep link**, extracts the `reference`, and calls backend to verify.
8. **Backend verifies transaction** and credits user's wallet.

---

### 🔧 Backend Endpoint: `POST /api/payments/initiate`

**Request:**

```json
{
  "user_id": "abc123",
  "amount": 500000,  // in kobo or cents
  "wallet_id": "wallet_001"
}
```

**Backend Logic:**

* Calls Paystack/Flutterwave `/initialize` or `/payments` API
* Includes:

  * `email`, `amount`, `currency`
  * Unique `reference` (e.g., `cluster_<user_id>_<timestamp>`)
  * `redirect_url`: a deep link or hosted confirmation page

**Response:**

```json
{
  "authorization_url": "https://checkout.paystack.com/abc123",
  "reference": "cluster_user123_1728921"
}
```

---

### 📱 Flutter App Implementation

#### WebView Approach

* Use `webview_flutter` or `flutter_webview_plugin`
* Load `authorization_url` in the WebView
* Monitor `onUrlChanged` for:

  * Deep link: `cluster://payment-complete?reference=xyz`
  * OR confirmation page: extract reference from `window.location.href`

#### Deep Linking

* Use [`uni_links`](https://pub.dev/packages/uni_links)
* Register custom URI scheme: `cluster://`
* On redirect:

  * Extract `reference` from query params
  * Call: `GET /api/payments/verify/:reference`

---

### ✅ Transaction Verification

* Backend verifies using PSP verify API:

  * Paystack: `GET /transaction/verify/:reference`
  * Flutterwave: `GET /transactions/:id/verify`
* Validates:

  * Status: `"success"`
  * Reference matches expected user/wallet
* Credits user wallet and sends confirmation response to app

---

### 🔐 Security Notes

* All PSP secret keys are used on backend only.
* Client cannot initiate or verify transactions directly.
* Webhooks should be used as secondary confirmation.

---

### 🧪 Sample Deep Link

* Example: `cluster://payment-complete?reference=cluster_user123_1728921`
* Deep link handler should:

  * Parse `reference`
  * Call backend verification API
  * Show success/failure status

---

Let me know if you want this saved as a Markdown, Notion page, or embedded in your codebase as docstring or inline comments.
