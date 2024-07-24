from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
import oci
import base64
import uuid
import requests
import io
import os
import logging
import json
import oci.ai_document
import concurrent.futures
import oci.object_storage
from concurrent.futures import ThreadPoolExecutor, wait

import smtplib
import email.utils
from email.message import EmailMessage
import ssl
from fdk import response



signer = oci.auth.signers.get_resource_principals_signer()
COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaafuifib7wfdamukivh4hwmiimf6snqq5kpww4siqys6kfysvvoo2a"
NAMESPACE_NAME = "idmmbvnn4gnv"
BUCKET_NAME = "Email_Storage"
FOLDER_NAME = "PurchaseOrder/"
OUTPUT_FOLDER_NAME = "Customer_PurchaseOrder_output/"
ARCHIVE_FOLDER_NAME = "Archive/Input/"
ARCHIVE_OUTPUT = "Archive/Output/"
PREFIX = "KV"

model_ids = {
    "header": "ocid1.aidocumentmodel.oc1.iad.amaaaaaaisynthiak7sbfvlv3uo2wkd6ymmwffyat6z5bjhgne2zxinzwqnq",
    "separateLine": "ocid1.aidocumentmodel.oc1.iad.amaaaaaaisynthiax3bbkxpdekgg7wp6m4gmatmcl4yagffaifcebnz4sn5a",
    "line": "ocid1.aidocumentmodel.oc1.iad.amaaaaaaisynthiawn3y6mhrizxj73xuvram2khw5m4vp4basrotyn7fkriq"
}

output_location = oci.ai_document.models.OutputLocation(
    namespace_name=NAMESPACE_NAME,
    bucket_name=BUCKET_NAME,
    prefix=PREFIX
)


SENDER = 'faiscan@automus.com'
SENDERNAME = 'FAIScan'
USERNAME_SMTP = 'ocid1.user.oc1..aaaaaaaabhdqmxs4mmiy5uvcuykhwmfo6aajgz2mukr5qan7aiv7nhs6djfq@ocid1.tenancy.oc1..aaaaaaaa2t46qhoc5kon5rxqmupaxm4rnr4hzhfzylz77y6cotgrhavhl3rq.iu.com'
HOST = "smtp.us-ashburn-1.oraclecloud.com"
PORT = 587
PASSWORD_SMTP = 'mS3eB(WltZU8[D[B!4[l'


SUBJECT_SUCCESS = 'Order Created Successfully'
BODY_SUCCESS = 'Your order has been successfully created.'

SUBJECT_FAILURE = 'Failed to Create Order'
BODY_FAILURE = 'Failed to create order. Please check and try again.'

def list_objects_in_bucket(namespace_name, bucket_name, prefix):
    """Lists objects in the specified bucket with the given prefix."""
    object_storage_client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    list_objects_response = object_storage_client.list_objects(namespace_name, bucket_name, prefix=prefix)
    return [obj.name for obj in list_objects_response.data.objects]

def extract_recipient_and_filename(object_name):
    """Extracts recipient email and filename from object name."""
    filename = object_name.split('/')[-1]
    parts = filename.split(',')
    if len(parts) >= 2:
        recipient_email = parts[0].strip()
        file_name = parts[1].strip()
        return recipient_email, file_name
    return None, None

def send_email(recipient_email, subject, body):
    """Sends an email to the specified recipient."""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = recipient_email
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP(HOST, PORT)
        server.starttls(context=context)
        server.login(USERNAME_SMTP, PASSWORD_SMTP)
        server.send_message(msg)
        print(f"Email successfully sent to {recipient_email}!")
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")
    finally:
        server.quit()

def create_processor_job(object_name, model_id):
    """Creates a processor job for AI Document Processing."""
    print('in create_processor_job')
    object_location = oci.ai_document.models.ObjectLocation(
        namespace_name=NAMESPACE_NAME,
        bucket_name=BUCKET_NAME,
        object_name=object_name
    )
    key_value_extraction_feature = oci.ai_document.models.DocumentKeyValueExtractionFeature(model_id=model_id)
    create_processor_job_details = oci.ai_document.models.CreateProcessorJobDetails(
        display_name=str(uuid.uuid4()),
        compartment_id=COMPARTMENT_ID,
        input_location=oci.ai_document.models.ObjectStorageLocations(object_locations=[object_location]),
        output_location=output_location,
        processor_config=oci.ai_document.models.GeneralProcessorConfig(features=[key_value_extraction_feature])
    )
    print('end create_processor_job')
    return create_processor_job_details

def extract_key_value_pairs(response):
    """Extracts key-value pairs from AI Document Processing response."""
    kv_pairs = []
    for page_data in response["pages"]:
        key_value_fields = page_data.get("documentFields", [])
        for field in key_value_fields:
            if field["fieldType"] == "KEY_VALUE":
                label_name = field["fieldLabel"]["name"]
                value_data = field["fieldValue"]
                value_name = value_data["value"]
                confidence_score = field["fieldLabel"].get("confidence", None)
                if confidence_score is not None and confidence_score >= 0.3:
                    kv_pairs.append({"label": label_name, "value": value_name, "confidence": confidence_score})
            else:
                items = field["fieldValue"]["items"]
                for item in items:
                    sub_items = item["fieldValue"]["items"]
                    for sub_item in sub_items:
                        label_name = sub_item["fieldLabel"]["name"]
                        value_name = sub_item["fieldValue"]["value"]
                        confidence_score = sub_item["fieldLabel"].get("confidence", None)
                        if confidence_score is not None and confidence_score >= 0.3:
                            kv_pairs.append({"label": label_name, "value": value_name, "confidence": confidence_score})
    return kv_pairs

def is_valid_json(json_string):
    """Checks if a string is a valid JSON."""
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False

def create_sales_order(kv_pairs):
    """Simulates creating a sales order and returns order number or error."""
    order_number = None
    error = None

    # Mock implementation of creating a sales order
    # values_dict = {item['label']: item['value'] for item in kv_pairs}
    # object_name = values_dict.get("File Name")
    # customer_po_number = values_dict.get("Customer Number", 59300)
    # ordered_date = datetime.strptime(values_dict.get("DATE"), '%m/%d/%Y')
    # bill_to_party_name = "Dixon Industries"
    # ship_to_party_name = None
    print ('start')
    values_dict = {item['label']: item['value'] for item in kv_pairs}
    file_name = values_dict.get("File Name")
    customer_po_number = values_dict.get("Customer Number")
    bill_to_company_name = values_dict.get("BillTo Company Name\t", "")
    ship_to_company_name = values_dict.get("ShipTo Company Name", "")
    
    payment_terms = values_dict.get("PaymentTerms", "")
    contact_name = values_dict.get("ContactName", "")
    
    item_no = values_dict.get("ITEM NO", "")
    qty = values_dict.get("Qty", "")
    ship_date = (datetime.now() - timedelta(days=2)).isoformat()
    current_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    item_no_list = item_no.split()
    qty_list = qty.split()
    lines = []
    
    print ('start', values_dict)
    
    # Looping to create multiple lines
    
    for i, (item, quantity) in enumerate(zip(item_no_list, qty_list)):
        print('in for loop')
        line = {
            "SourceTransactionLineId": i + 1,
            "SourceTransactionLineNumber": i + 1,
            "SourceTransactionScheduleId": i + 1,
            "SourceScheduleNumber": str(i + 1),
            "TransactionCategoryCode": "ORDER",
            "TransactionLineType": "Buy",
            "ProductNumber": item,
            "OrderedQuantity": quantity,
            "OrderedUOM": "Ea"
        }
        lines.append(line)    
    
    # Extract only the file name from the object name
    print(lines)
    # file_name = object_name = object_name.split(',')[-1].strip()

    payload = {
        "SourceTransactionNumber": current_timestamp,
        "SourceTransactionSystem": "OPS",
        "SourceTransactionId": current_timestamp,
        "BusinessUnitName": "US1 Business Unit",
        "BuyingPartyName": bill_to_company_name,
        "RequestedShipDate": ship_date, 
        "PaymentTerms": "30 Net", 
        "RequestingBusinessUnitName": "US1 Business Unit",
        "FreezePriceFlag": False,
        "FreezeShippingChargeFlag": False,
        "FreezeTaxFlag": False,
        "SubmittedFlag": True,
        "SourceTransactionRevisionNumber": "1",
        "billToCustomer": [
            {
                "PartyName": bill_to_company_name,
                "AccountNumber": customer_po_number,
            }
        ],
        "shipToCustomer": [
            {
                "PartyName": ship_to_company_name,
            }
        ],
        "lines": lines
    }
    print("Payload: ", payload)
    
    try:
        print('trigger API - ', datetime.now().strftime('%Y%m%d%H%M%S'))
        url = "https://fa-ewki-dev6-saasfademo1.ds-fa.oraclepdemos.com/fscmRestApi/resources/11.13.18.05/salesOrdersForOrderHub/"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, data=json.dumps(payload),
                                 auth=HTTPBasicAuth("SCM_IMPL", "ct*Z8%5b"))
        print('trigger API - End', datetime.now().strftime('%Y%m%d%H%M%S'))
        if response.status_code == 201:
            print("Order created successfully.")
            response_json = response.json()
            order_number = response_json.get('OrderNumber')
            body = f"{BODY_SUCCESS}\nOrder Number: {order_number}"
            subject = f"Order Created Successfully: {file_name}"
        else:
            print(f"Failed to create order. Status code: {response.status_code}, Error: {response.text}")
            try:
                response_json = response.json()
                error_message = response_json.get('errorMessage', 'Unknown error')
            except ValueError:
                error_message = response.text
            body = f"{BODY_FAILURE}\nError: {error_message}"
            subject = f"Failed to Create Order: {file_name}"

    except requests.RequestException as e:
        print(f"Request error: {e}")
        body = f"{BODY_FAILURE}\nError: {str(e)}"
        subject = f"Failed to Create Order: {file_name}"

    return order_number, body, subject


def process_file(object_name, ai_service_document_client, object_storage_client, existing_json_files):
    """Process each file, extract key-value pairs, create sales order, and send email."""
    supported_extensions = ['jpg', 'png', 'pdf', 'tif']
    kv_pairs_dict = {ext: [] for ext in supported_extensions}
    print('in process file')
    for ext in supported_extensions:
        if object_name.lower().endswith(ext):
            recipient_email, file_name = extract_recipient_and_filename(object_name)
            if recipient_email and file_name:
                base_name = file_name.rsplit('.', 1)[0]
                output_json = f"{OUTPUT_FOLDER_NAME}{recipient_email},{base_name}.json"
                print('in for loop')
                
                if output_json in existing_json_files:
                    print(f"Already exists as {output_json}. Skipping processing.")
                    return

                print(f"Processing file: {object_name}")

                responses = []
                for model_name, model_id in model_ids.items():
                    processor_job_details = create_processor_job(object_name, model_id)
                    response = ai_service_document_client.create_processor_job_and_wait_for_state(
                        create_processor_job_details=processor_job_details,
                        wait_for_states=[oci.ai_document.models.ProcessorJob.LIFECYCLE_STATE_SUCCEEDED]
                    ).data
                    print(response)
                    responses.append(response)
                print(f"Response file: {responses}")
                kv_pairs = [{"label": "File Name", "value": object_name, "confidence": 1.0}]
                for response in responses:
                    result_object_name_prefix = f"{output_location.prefix}/{response.id}/{NAMESPACE_NAME}_{BUCKET_NAME}/results/"
                    list_objects_response = object_storage_client.list_objects(
                        namespace_name=output_location.namespace_name,
                        bucket_name=output_location.bucket_name,
                        prefix=result_object_name_prefix
                    )
                    result_object_names = [obj.name for obj in list_objects_response.data.objects]

                    for result_object_name in result_object_names:
                        if result_object_name.endswith('.json'):
                            try:
                                get_object_response = object_storage_client.get_object(
                                    namespace_name=output_location.namespace_name,
                                    bucket_name=output_location.bucket_name,
                                    object_name=result_object_name
                                )
                                response_content = json.loads(get_object_response.data.content.decode())
                                kv_pairs.extend(extract_key_value_pairs(response_content))
                            except oci.exceptions.ServiceError as e:
                                print(f"Failed to retrieve object: {result_object_name} with error: {e}")
                                
                if len(kv_pairs) <= 2:
                    print(f"Skipping file {object_name} because it not contains required labels and values.")
                    return

                print(f"Extracted key-value pairs: {kv_pairs}")
                try:
                    order_number, body, subject = create_sales_order(kv_pairs)
                    print(f"Order Number: {order_number}, Body: {body}, Subject: {subject}")

                    kv_pairs.append({"label": "Order Number", "value": order_number})
                    kv_pairs.append({"label": "Error_message", "value": "None"})

                except Exception as e:
                    error_message = str(e)
                    print(f"Failed to create order: {error_message}")

                    kv_pairs.append({"label": "Order Number", "value": ""})
                    kv_pairs.append({"label": "Error_message", "value": error_message})     

#                 order_number, body, subject = create_sales_order(kv_pairs)
#                 print(f"Order Number: {order_number}, Body: {body}, Subject: {subject}")

#                 kv_pairs.append({"label": "Order Number", "value": order_number})
                
                kv_pairs_dict[ext].extend(kv_pairs)
        
                for ext, kv_pairs in kv_pairs_dict.items():
                    if kv_pairs:
                        output_json = f"{OUTPUT_FOLDER_NAME}{recipient_email},{base_name}.json"
                        json_content = json.dumps(kv_pairs).encode("utf-8")
                        if is_valid_json(json_content):
                            object_storage_client.put_object(NAMESPACE_NAME, BUCKET_NAME, output_json, json_content)
                            print(f"JSON file for {ext} uploaded successfully as {recipient_email},{base_name}.json.")
                            
                            # Move the original file to Archive/Input Folder if JSON was uploaded successfully
                            try:
                                archive_response = object_storage_client.put_object(
                                    namespace_name=NAMESPACE_NAME,
                                    bucket_name=BUCKET_NAME,
                                    object_name=ARCHIVE_FOLDER_NAME + base_name,
                                    put_object_body=get_object_response.data.content,
                                    content_length=get_object_response.headers["Content-Length"]
                                )

                                if archive_response.status == 200:
                                    print(f"File {object_name} moved to Archive folder successfully.")

                                    object_storage_client.delete_object(
                                        namespace_name=NAMESPACE_NAME,
                                        bucket_name=BUCKET_NAME,
                                         object_name=object_name
                                    )
                                    print(f"Deleted original file {object_name} from PurchaseOrder folder.")

                            except oci.exceptions.ServiceError as e:
                                print(f"Failed to move file {object_name} to Archive/Input with error: {e}")
                                
                                
                            # json was uploaded sucessfuly, we move the original file to Archive/Output Folder
                            try:
                                archive_response = object_storage_client.put_object(
                                    namespace_name=NAMESPACE_NAME,
                                    bucket_name=BUCKET_NAME,
                                    object_name=f"{ARCHIVE_OUTPUT}{recipient_email},{base_name}.json",
                                    put_object_body=json_content,
                                    content_type="application/json"
                                )
                                if archive_response.status == 200:
                                    print(f"File {recipient_email},{base_name}.json moved to Archive/Output folder successfully.")

                            except oci.exceptions.ServiceError as e:
                                message = f"Failed to move file {recipient_email},{base_name}.json to Archive/Output with error: {e}"
                                print(message)          

                        else:
                            print(f"Invalid JSON format for {output_json}")
                                

                # Send email notification based on order creation success or failure
                if recipient_email:
                    send_email(recipient_email, subject, body)
                else:
                    print(f"Recipient email not found in object name: {object_name}")

# Handler function
def handler(ctx, data: io.BytesIO = None):
    object_storage_client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    ai_service_document_client = oci.ai_document.AIServiceDocumentClientCompositeOperations(
        oci.ai_document.AIServiceDocumentClient({}, signer=signer)
    )

    object_names = list_objects_in_bucket(NAMESPACE_NAME, BUCKET_NAME, FOLDER_NAME)
    print(f"Files found in PurchaseOrder folder: {object_names}")

    if not object_names:
        print("No files present in PurchaseOrder folder, to process..")
        return
    existing_json_files = list_objects_in_bucket(NAMESPACE_NAME, BUCKET_NAME, OUTPUT_FOLDER_NAME)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(process_file, object_name, ai_service_document_client, object_storage_client, existing_json_files)
            for object_name in object_names
        ]
        wait(futures)
    return response.Response(
        ctx, response_data=json.dumps({"status": "Processing Completed"}),
        headers={"Content-Type": "application/json"}
    )
