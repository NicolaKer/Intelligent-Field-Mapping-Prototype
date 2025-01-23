import boto3
import json
import sys
import time

'''Adapted from: https://docs.aws.amazon.com/textract/latest/dg/async-analyzing-with-sqs.html
Date: 14 October 2023

Please note: Docstring comments were generated by ChatGTP'''


class ProcessType:
    ANALYSIS = 1


class DocumentProcessor:
    """
    A class for processing documents using Amazon Textract.
    """

    jobId = ''
    region_name = ''

    roleArn = ''
    bucket = ''
    document = ''

    sqsQueueUrl = ''
    snsTopicArn = ''
    processType = ''

    def __init__(self, role, bucket, document, region, access_key, secret_access_key):

        """
        Initializes the DocumentProcessor with AWS credentials and document information.

        :param role: Amazon Textract Role ARN.
        :param bucket: Name of the AWS S3 bucket where the document is stored.
        :param document: Name of the document in the S3 bucket.
        :param region: AWS region where the S3 bucket and Textract service are located.
        :param access_key: AWS access key ID for authentication.
        :param secret_access_key: AWS secret access key for authentication.
        """

        self.roleArn = role
        self.bucket = bucket
        self.document = document
        self.region_name = region

        self.textract = boto3.client('textract', region_name=self.region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
        self.sqs = boto3.client('sqs', region_name=self.region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
        self.sns = boto3.client('sns', region_name=self.region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)

    def ProcessDocument(self, type, queries):
        """
        Processes the document using Amazon Textract based on the specified processing type and queries.

        :param type: Processing type (currently supports ProcessType.ANALYSIS).
        :param queries: Queries to be used for Textract analysis.
        :return: List of Textract response objects.
        """
         
        jobFound = False

        self.processType = type
        validType = False

        #this list holds all the response objects returned by Textract for the given document
        responses = []

        # For document analysis, select which features you want to obtain with the FeatureTypes argument
        #response is contains the job id
        if self.processType == ProcessType.ANALYSIS:
            response = self.textract.start_document_analysis(
                DocumentLocation={'S3Object': {'Bucket': self.bucket, 'Name': self.document}},
                FeatureTypes=["QUERIES"],
                                       QueriesConfig=queries,
                NotificationChannel={'RoleArn': self.roleArn, 'SNSTopicArn': self.snsTopicArn})
            print('Processing type: Analysis')
            validType = True

        if validType == False:
            print("Invalid processing type. Choose Detection or Analysis.")
            return

        print('Start Job Id: ' + response['JobId'])
        dotLine = 0
        while jobFound == False:
            sqsResponse = self.sqs.receive_message(QueueUrl=self.sqsQueueUrl, MessageAttributeNames=['ALL'],
                                                   MaxNumberOfMessages=10)

            if sqsResponse:

                if 'Messages' not in sqsResponse:
                    if dotLine < 40:
                        print('.', end='')
                        dotLine = dotLine + 1
                    else:
                        print()
                        dotLine = 0
                    sys.stdout.flush()
                    time.sleep(5)
                    continue

                for message in sqsResponse['Messages']:
                    notification = json.loads(message['Body'])
                    textMessage = json.loads(notification['Message'])
                    print(textMessage['JobId'])
                    print(textMessage['Status'])
                    if str(textMessage['JobId']) == response['JobId']:
                        print('Matching Job Found:' + textMessage['JobId'])
                        jobFound = True
                        responses = self.GetResults(textMessage['JobId'])

                        self.sqs.delete_message(QueueUrl=self.sqsQueueUrl,
                                                ReceiptHandle=message['ReceiptHandle'])
                    else:
                        print("Job didn't match:" +
                              str(textMessage['JobId']) + ' : ' + str(response['JobId']))
                    # Delete the unknown message. Consider sending to dead letter queue
                    self.sqs.delete_message(QueueUrl=self.sqsQueueUrl,
                                            ReceiptHandle=message['ReceiptHandle'])

        print('Done!')
        return responses

    
    def CreateTopicandQueue(self):

        millis = str(int(round(time.time() * 1000)))

        # Create SNS topic
        snsTopicName = "AmazonTextractTopic" + millis

        topicResponse = self.sns.create_topic(Name=snsTopicName)
        self.snsTopicArn = topicResponse['TopicArn']

        # create SQS queue
        sqsQueueName = "AmazonTextractQueue" + millis
        self.sqs.create_queue(QueueName=sqsQueueName)
        self.sqsQueueUrl = self.sqs.get_queue_url(QueueName=sqsQueueName)['QueueUrl']

        attribs = self.sqs.get_queue_attributes(QueueUrl=self.sqsQueueUrl,
                                                AttributeNames=['QueueArn'])['Attributes']

        sqsQueueArn = attribs['QueueArn']

        # Subscribe SQS queue to SNS topic
        self.sns.subscribe(
            TopicArn=self.snsTopicArn,
            Protocol='sqs',
            Endpoint=sqsQueueArn)

        # Authorize SNS to write SQS queue
        policy = """{{
  "Version":"2012-10-17",
  "Statement":[
    {{
      "Sid":"MyPolicy",
      "Effect":"Allow",
      "Principal" : {{"AWS" : "*"}},
      "Action":"SQS:SendMessage",
      "Resource": "{}",
      "Condition":{{
        "ArnEquals":{{
          "aws:SourceArn": "{}"
        }}
      }}
    }}
  ]
}}""".format(sqsQueueArn, self.snsTopicArn)

        response = self.sqs.set_queue_attributes(
            QueueUrl=self.sqsQueueUrl,
            Attributes={
                'Policy': policy
            })

    def DeleteTopicandQueue(self):
        self.sqs.delete_queue(QueueUrl=self.sqsQueueUrl)
        self.sns.delete_topic(TopicArn=self.snsTopicArn)
      
                
    def GetResults(self, jobId):

        """
        Retrieves the analysis results for the specified job ID using Amazon Textract.

        :param jobId: Job ID returned by Amazon Textract for document analysis.
        :return: List of Textract response objects.
        """

        maxResults = 1000
        paginationToken = None
        finished = False
        responses = []
        pages = 1

        while finished == False:

            response = None

            if self.processType == ProcessType.ANALYSIS:
                if paginationToken == None:
                    response = self.textract.get_document_analysis(JobId=jobId,
                                                                   MaxResults=maxResults)

                else:
                    response = self.textract.get_document_analysis(JobId=jobId,
                                                                   MaxResults=maxResults,
                                                                   NextToken=paginationToken)

            responses.append(response)
            pages = pages + 1

            if 'NextToken' in response:
                paginationToken = response['NextToken']
            else:
                finished = True

        return responses
    



