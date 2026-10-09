\# Zecpath API Developer Guide



\## 1. Overview



Zecpath is a recruitment platform with backend APIs for candidate and employer workflows, job management, applications, AI-assisted interview workflows, notifications, and related services.



This guide explains how developers can access the API documentation, authenticate requests, and test endpoints.



\## 2. Local Development Setup



\### Prerequisites



\- Python and the project's required Python packages

\- Access to the configured PostgreSQL database

\- Any supporting services required by the project, such as Redis and Docker



\### Install dependencies



Activate the project's virtual environment and install the dependencies:



```cmd

pip install -r requirements.txt

```



\### Run Django checks



```cmd

python manage.py check

```



\### Start the development server



```cmd

python manage.py runserver

```



The examples below assume the server is running locally at `http://127.0.0.1:8000`.



\## 3. API Documentation



\### Swagger UI



Open:



`http://127.0.0.1:8000/api/docs/`



Swagger UI lets developers browse documented endpoints, inspect request parameters and request bodies, review generated response schemas, and execute API requests.



\### OpenAPI schema



Open:



`http://127.0.0.1:8000/api/schema/`



This endpoint serves the generated OpenAPI schema in YAML format. The schema can be used by compatible API tools and documentation clients.



\### Django admin



Open:



`http://127.0.0.1:8000/admin/`



Access requires a valid Django admin account.



\## 4. Authentication



The API documentation is configured for JWT bearer authentication.



\### Obtain tokens



Use the login endpoint shown in Swagger UI. The documented login operation is:



\- \*\*Method:\*\* POST

\- \*\*Path:\*\* `/api/login/`

\- \*\*Request body:\*\* Username and password, as shown in the generated schema



A successful login returns authentication tokens according to the login endpoint's response schema.



Treat access and refresh tokens as secrets. Do not commit tokens to source control or include them in screenshots, logs, or shared documentation.



\### Authorize requests in Swagger UI



1\. Open the Swagger UI page.

2\. Execute the login endpoint with valid test credentials.

3\. Copy the access token from the response without sharing it.

4\. Click \*\*Authorize\*\*.

5\. Enter the access token in the format requested by the Swagger authentication dialog. For a bearer-token field, this is normally the token itself.

6\. Confirm authorization and execute an endpoint that requires authentication.



Use the access token for protected requests. Refresh tokens are used to obtain new access tokens through the configured refresh endpoint; they are not substitutes for access tokens on ordinary API requests.



\### Authentication and permissions



Authentication and authorization are different:



\- Authentication establishes which user is making a request.

\- Permissions determine whether that user can perform the requested action.



A valid token does not guarantee access to every endpoint. Candidate, employer, and administrator operations may have different permission requirements.



\## 5. Testing APIs



\### Using Swagger UI



1\. Expand the endpoint you want to test.

2\. Review its HTTP method, path, parameters, request body, and documented responses.

3\. Click \*\*Try it out\*\*.

4\. Enter the required values.

5\. Execute the request.

6\. Inspect the HTTP status, response body, and response headers.



\### Using Postman



1\. Create a request using the method and URL shown in Swagger.

2\. Add the required request body or query parameters.

3\. For protected endpoints, select Bearer Token authentication and supply a valid access token.

4\. Send the request and inspect the status code and JSON response.



Use test accounts and non-production data when experimenting with requests that create, update, delete, or trigger workflows.



\## 6. Understanding Responses



Swagger's \*\*Example Value\*\* is generated from the OpenAPI schema. It may contain placeholder values and does not necessarily represent actual database records or the exact result of a particular request.



The \*\*Server response\*\* section shows the result of the request you executed.



For example, an actual response body of:



```json

\[]

```



is an empty JSON array. It means the request returned no items; it is not the same as a request failure.



Always distinguish the generated example from the actual server response and check the HTTP status code.



\## 7. API Endpoint Reference



The application routes are included under the `/api/` prefix. Browse Swagger UI for the currently documented endpoints and their methods, parameters, request bodies, authentication requirements, and response schemas.



The OpenAPI schema may not yet describe every endpoint completely. If an operation is missing or its schema appears inaccurate, verify the corresponding URL configuration, view, serializer, permissions, and actual response before relying on the generated documentation.



\## 8. Security Notes



\- Never commit passwords, access tokens, refresh tokens, API keys, or other secrets.

\- Keep environment-specific credentials outside source control.

\- Do not use production credentials for local API testing.

\- Use only the permissions required for the operation.

\- Protect endpoints that trigger sensitive actions or modify application data.

\- Do not expose payment credentials or webhook secrets in API examples.

\- Treat authentication tokens shown in shared screenshots as exposed and revoke or rotate them as appropriate.



\## 9. Useful Commands



Run Django's system check:



```cmd

python manage.py check

```



Generate an OpenAPI schema file for inspection:



```cmd

python manage.py spectacular --file schema.yaml

```



Validate the generated schema:



```cmd

python manage.py spectacular --validate --file schema.yaml

```



Schema validation can report issues for views whose serializers or querysets cannot be inferred. Review those messages before treating the generated schema as complete.



\## 10. Documentation Maintenance



When adding or modifying an API endpoint:



1\. Verify its URL and HTTP method.

2\. Document the actual request fields and validation rules.

3\. Document successful and relevant error responses.

4\. Confirm its authentication and permission requirements.

5\. Test the endpoint with a valid request.

6\. Update the OpenAPI schema or endpoint annotations when automatic inference is insufficient.

7\. Update this guide if setup or authentication instructions change.



