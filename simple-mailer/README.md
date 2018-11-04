# README #

# Simple mailer

* FOR RUNNING IN FRESH ENVIRONMENT ON LINUX

. source-me-first

* TO SERVE CONTENT TO WEB BROWSER

./serve

* TO ADD TO GIT REPOSITORY

./deploy

* TO VIEW SENDGRID INFO OF HEROKU ADDON

./show-sendgrid

* TO CHANGE PROJECT SETTINGS, OPEN

config.py

* FOR LOG FILE CREATED DURING RUN, OPEN

log.txt


# INSTRUCTIONS #

1.	User will log into the web server mailer page ( htaccess or similar security)

2.	This page will have fields as listed below:

•	MAILING NAME

o	This will be the unique name of the mailing that is to be sent

•	UPLOAD file (text or csv) see attached sample file.

o	As soon as file is uploaded show how many contacts were imported

o	The format of file will be First name, last name, email address, school  

o	All these fields in the database will be wildcards meaning mentioning them in SUBJECT or BODY of email will use the entry fields

	Example: NAME, how are you? Will make each email personalized with users NAME. Maxim, how are you?

•	FROM email:

•	SUBJECT: 

•	BODY of email (text only)

•	Sendgrid API to use:
3.	User clicks SEND button

4.	First thing is to check score using MAIL TESTER API https://www.mail-tester.com/manager/api-documentation.html if email score is:

a.	higher than 7

i.	start sending messages to all emails in the imported emails

b.	lower than 6.9

i.	stop sending and show message: Score too low: XX	 

ii.	Reasons for Low score

5.	Once all messages are sent in the batch send report to namecaller@yandex.com

a.	Subject: Simple Mailer

b.	Total emails sent: XX

6.	Do not store any email or data on the server. Keep only the message history (DATE, MALING NAME, NUMBER OF EMAILS SENT, SUCCESS/FAIL)

### What is this repository for? ###

* Quick summary
* Version
* [Learn Markdown](https://bitbucket.org/tutorials/markdowndemo)

### How do I get set up? ###

* Summary of set up
* Configuration
* Dependencies
* Database configuration
* How to run tests
* Deployment instructions

### Contribution guidelines ###

* Writing tests
* Code review
* Other guidelines

### Who do I talk to? ###

* Repo owner or admin
* Other community or team contact
