# Creating, Building, and Invoking a Function on OCI.

Below you see sample screen of Cloud Shell and Code Editor:

![24 07 2024_10 29 17_REC](https://github.com/user-attachments/assets/53a2bb4d-bb50-4fbe-b93c-8176a28b6113)

Begin your Cloud Shell session: 
_Launch Cloud Shell_

**Setup fn CLI on Cloud Shell:**

Use the context for your region: 
- fn list context
- fn use context us-ashburn-1

Update the context with the function's compartment ID: 
- fn update context oracle.compartment-id ocid1.compartment.oc1..aaaaaaaafuif....

Provide a unique repository name prefix to distinguish your function images from other people’s. For example, with 'jdoe' as the prefix, the image path for a 'hello' function image is '<region-key>.ocir.io/<tenancy-namespace>/jdoe/hello:0.0.1'
- fn update context registry iad.ocir.io/idmmbvnn4gnv/[repo-name-prefix]

Generate Auth Token

Log into the Registry using the Auth Token as your password:
- docker login -u 'idmmbvnn4gnv/abc@comanyname.com' iad.ocir.io

Verify your setup by listing applications in the compartment
- fn list apps

**Create, deploy, and invoke your function**

- Generate a 'hello-world' boilerplate function
fn init --runtime python hello-python

Switch into the generated directory:
- cd hello-python

Deploy your function:
- fn -v deploy --app FAIS

Invoke your function:
- fn invoke FAIS hello-python
