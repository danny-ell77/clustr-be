# ClustR Technical Requirements 

### **Table of Contents**

[1 Introduction](#1-introduction)

[2 Third-Party Partnerships](#2-third-party-partnerships)

[2.1 Payment Processors](#2.1-payment-processors)

[2.1.1 Requirements](#2.1.1-requirements)

[3 Technical Requirements](#3-technical-requirements)

[4 Data Security](#4-data-security)

[6 Integration and API](#6-integration-and-api)

[7 Deployment](#7-deployment)

## 

## 

## 1 Introduction {#1-introduction}

This document serves as both an overview of the technical aspects related to the ClustR product and an outline of the essential technical requirements and third-party partnerships. It is important to emphasize that this document is a living resource that will undergo periodic review and enhancement to provide more specific details about the project's underlying technology.

## 2 Third-Party Partnerships {#2-third-party-partnerships}

### 2.1 Payment Processors {#2.1-payment-processors}

1. Paystack: The integration with Paystack serves the primary purpose of enabling our project to accept online payments securely and efficiently. By integrating with Paystack, we aim to provide our customers with a seamless and convenient payment experience, which is crucial for the success of our project.  
2. Flutterwave: Flutterwave seems to provide all of the features Paystack provides. However, they also provide a Bill payment API that allows us to process bill payments through them making it convenient and easy to process 

#### 2.1.1 Requirements {#2.1.1-requirements}

To successfully integrate with our payment partners, our project needs to meet the following technical requirements:

API Keys: Obtain API keys, including a secret key for server-side operations. A test key for debugging purposes and a live key for production 

Webhooks Implementation: Set up webhooks to receive real-time notifications for payment updates and other transaction-related events. Proper handling of webhooks is essential for order fulfillment and transaction verification.

Compliance: Adhere to the processor’s security and compliance standards to protect customer data. This may involve periodic security audits and updates to our project's infrastructure.

## 3 Technical Requirements {#3-technical-requirements}

Programming Languages: Python 3.11

Frameworks and Libraries: Django 4.2.7, Django Rest Framework 3.9.3

Web Server: Gunicorn  21.2.0, Daphne 4.0.0  (For WebSockets)

Server Environment: Heroku Dynos or AWS K8s Cluster

Database: PostgreSQL 14

Authentication and Authorization: JWT Authentication with RSA Encryption

Third-Party Integrations: Paystack, Flutterwave

## 4 Data Security {#4-data-security}

Conventionally, the communication between our clients and the web API will be encrypted by TLS, provided by established SDKs for making API requests to the server. This encryption layer serves as the first line of defense to secure data transmission for our users.

Passwords: Passwords are generally hashed before they are stored in the database, this is common industry practice. When passwords are confirmed the received password is matched with the password belonging to the account specified. If the hashes aren’t equal the received password is invalid.

JWT Authentication: A secure token is passed between the web server and its clients (web & mobile) to be used as a form of authenticating users using these clients to make requests to the platform

## 6 Integration and API {#6-integration-and-api}

Due to the platform’s utility features, we’ll need to integrate with respective third-party utility providers e,g, Electricity, DSTV, water, etc.

<!-- ## 7 Deployment {#7-deployment}

There are two deployment strategies we could explore:

1. Heroku (3 Dynos) One for handling web API requests. Another for managing asynchronous tasks and a third for managing the database system. This needs to be more sophisticated and may not be able to cope with changing business requirements in the future as well as scalability. Further research is going to be done on this. I’d propose this deployment infrastructure be used only for testing and staging purposes.

2. AWS Kubernetes offers a robust and sophisticated solution for addressing scalability concerns in the face of exponential usage growth. However, its viability requires further research and verification.
 -->
