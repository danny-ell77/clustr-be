ClustR Application Design

Bounded Contexts :

- Members  
1.  Onboarding  
2. Help Desk  
3. Chat  
4. Announcement  
5. Access Control  
6. Poll  
7. Meetings  
8. SOS  
9. E-Wallet  
10. Payments  
11. Rule Book  
12. Documents  
13. Child Security  
14. Marketplace  
15. Settings  
16. Home Servicemen Directory  
17. Domestic Staff Tracker  
    

 - Management
 1.  Onboarding
 2. Help Portal (Annouencements, Help DEsk/Chat, meetings scheduling(Zoom integration))
 3. ACcess Control (Security)
 4. Accounting (Estate invoicing, tennant/landlord eststae dues payments, financial reports)
 5. Shift Management (logging and scheduling shifts)
 6. Property management (maintenance and tenenat management (dues, fees, etc))

Onboarding:  
Objects:

1. User (Emergency Contacts\[prolly a JSONField\])  
2. Permissions

Help Desk  
Objects:  
1\. Complaint (Owner, Issue Number, Heading, Description, Photo, Status, Created By, Date Created, Comments)

Announcement  
Objects:

1. Announcement(Owner, Body, Assets\[Images/Files\], Comments, Views?, Likes? Constraint=\>Only Admins can publish announcements)

Access Control  
Events \-\> Guests \-\> Invitations  
Guests \-\> Invitations

The system has a background schedule that checks for expired invitations and flags them  
Overstay visitors are those visitors that have an expected exit less than now and have not checked- out   
Active visitors are those visitors that have an expected exit greater than now and have not checed-out  
Expected Visitors are those visitors that have an expected exit greater than now and have not checked-in  
Invitations with both check-in and check out are marked as in-active and cannot be used again  
Objects:

1. Invitations (Scheduled-for, Expires-At, recurring(bool), Category, Access Code\!\!, Bar-Code-Url, Status \[Approved | Revoked\], \[Checked-in-at, Checked-out-at\]--\> might need to be extrapolated to a new model with a relationship to Invitations)  
2. Guests (Name, Email, Phone, Photo?)  
3. Events (Title, Description)

Polls  
Objects:  
Poll (Owner, Created-By, title, status\[draft | published\], published\_at, duration, constraint=\> polls with durations can’t take votes after the duration expires)  
Options (title, votes, poll, voters)  
PollConfig/ PollSettings ()  
Responses (created-by, timestamp, poll, option)

SOS  
Objects:  
Emergency (Owner, Category\[Health | Robbery | Domestic Violence\], Created-At)

E-Wallet

- The Payment Processor could be through Paystack, Flutter, or the Wallet System.

Processing a transaction through the wallet system aims to give a seamless experience in which case the user won’t have to go through the third-party processor using debit/credit cards, even though the wallet system uses the processor in the background 

- Inbound / Outbound flows of cash are treated as transactions.   
- Users can create utility bills and schedule them \[only for wallet processors\]. They get a set of reminder emails days before the scheduled time.  
- Admins can create bills for General Estate management  
- A setting configuration should be provided to provide users the flexibility to manage their automation e.g. Users can opt-in for reminders only and approve the scheduled payment whenever they like  
- Clsutr \- User \- Wallet \- Transactions \- Bill | BillingCycle

Objects:  
Wallet (Owner, Balance, Cap, Status, CheckSum)  
Bill (Title, Amount, Due, Discount, schedule)  
Transaction (Owner, processor, processor-meta-data, status \[falied | success\], title, category \[\])  
Proposed Properties:  
CustomerId (string?): The identifier of the customer initiating the transaction.  
DebitAccountNumber (string?): The account number from which funds are debited.  
DebitAccountName (string?): The name associated with the debiting account.  
DestinationBankCode (string?): The bank code of the destination bank in case of inter-bank transactions.  
DestinationBankName (string?): The name of the destination bank.  
CreditAccountNumber (string?): The account number to which funds are credited.  
CreditAccountName (string?): The name associated with the crediting account.  
TransactionType (TransactionType?): An enumerated type representing the type of transaction (e.g., Local Transfer, Inter-Bank Transfer, AirTime).  
TransactionReference (string?): A unique reference identifier for the transaction.  
BillerId (string?): The identifier of the biller involved in the transaction.  
BillerName (string?): The name of the biller.  
PaymentItemName (string?): The name of the payment item associated with the transaction.  
PaymentItemCode (string?): The code representing the payment item.  
Narration (string?): A description or comment associated with the transaction.  
Currency (string?): The currency in which the transaction is conducted.  
Amount (decimal): The amount involved in the transaction.  
Fee (decimal?): The fee charged for the transaction.  
SessionId (string?): The session identifier related to the transaction.  
PaymentReference (string?): A reference identifier associated with the payment.  
Status (string?): The status of the transaction.  
ResponseCode (string?): The response code returned for the transaction.  
RecordType (RecordType?): An enumerated type representing the record type (e.g., Debit, Credit).  
RechargePIN (string?): The PIN associated with recharge transactions.  
CustomerAddress (string?): The address of the customer initiating the transaction.

Enums  
TransactionType Enum  
LocalTransfer (1): Represents a local funds transfer.  
InterBankTransfer (2): Represents an inter-bank funds transfer.  
AirTime (3): Represents a transaction related to airtime purchase.  
BillPayment (4): Represents a bill payment transaction.  
CardRequest (5): Represents a request for a new card.  
Saving (6): Represents a savings-related transaction.  
RecordType Enum  
Debit (1): Represents a debit transaction.  
Credit (2): Represents a credit transaction.

Transfer?

Rule Book  
Objects:  
EstateGuidline (estate, text\_body\[Should have rich text/hyper-text formatting\], created\_at, create\_by)

Documentation  
Objects:  
Documents (Title, ResourceUrl\<Amazon\>\[File/Image\], uploaded\_by, Owner, format\[pdf | docx | png | jpg\], category\[Announcement | Reciept\], size)

Child Security  
Objects:  
Ward (Owner, Profile Picture, First Name, Last Name, Phone, Email, Unit No., Date of birth, Gender, Emergency Contacts?-\>JSONField?)  
Exits(Owner, ward, expected\_return, status \[Pending | Approved | Denied \], verified\_at, gateman, note, exit\_code, Reason, exited\_at, entry\_at)

MarketPlace

- User activity needs to be tracked so accurate product listings can be shown on the list page

Objects:  
Seller: First Name, Last Name, phone number, email, location, is\_resisdent  
Post/Ad/Listing: Title, Resource\[Image\], Description, Tags\[reverse-relationship\], Amount, Discount, total\_rating, saved\_by\[Many To many Relationship with Account Users\], status\[Draft | Published\], PublishedBy\<Seller\>  
Review: comment, rating, Ad/Post

Settings  
Objects:  
UserProfile: (Estate, Unit, First Name, Last Name, Phone, Email, email\_token, wallet\_pin\_hash, email\_verified, phone\_verified, profileImageURL,  passwordTries, pinTries, emailConfiemdAt, clustrId, ClstrAccessCode, DEviceId, Wallet\[One-To-One Relation\], wallet\_username)  
USerConfiguration: (Owner, Enable Push notification?)

Home Service Directory:  
Objects:  
ServiceMen: (Estate, Name, Location,Phone Number, Email, Service Category, Booked\_by\[Many To many Relationship with Account Users\])

Domestic Staff:  
Objects:  
Staff: (Owner, Estate,Profile Picture,  Name, Location,Phone Number, Email, access\_code, Role)