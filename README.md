# Intelligent-Field-Mapping-Prototype

## Description:
 
This prototype aims to show how AWS services can be used to help reduce manual entry of a new employee's information into an employer's system by extracting the information directly from onboarding forms.

This prototype automatically populates four text fields, namely first name, last name, employment start date, and IRD number, by extracting the information required by these fields from an uploaded employment agreement and IR330 Tax Code Declaration form.
 
To achieve this, the prototype sends the uploaded documents to Amazon Textract to extract text and important details from these uploaded documents. Once the prototype receives the extracted information back from Textract, it uses this information to automatically populate the four text fields on its webpage with the required information.

This prototype was created as part of a university group project.


## Configuration:

Before running the application:

1. See https://docs.aws.amazon.com/textract/latest/dg/api-async-roles.html to configure Amazon Textract correctly for asynchronous operations. Once 
configured, set the following variables in the flask_app.py file: 

- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_BUCKET_NAME
- REGION_NAME
- ROLEARN

2. Install the required Python packages.
- boto3==1.24.28
- Flask==2.2.2
- python_dateutil==2.8.2

3. Run the Flask application (flask_app.py).

## My contribution:

I worked on the back end of the application.
