# company API (1.0.0)

Download OpenAPI specification:[Download](https://static.company.site/openapi.json)

License: UNLICENSED

API specification for the company External API

## CreatePresignedUrl

Create an embedded url for a project

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| companyUserAttributes | object  A map of attributes meant to populate company\_user\_attributes in the app for the running user. This must be a string to string map. For more complexity, you can do json serialization |
| scope | Array of strings  Optionally include additional permissions for a user to do in an embedded app. Valid scopes include:  EXPORT\_PDF: allow users to download the app as a pdf EXPORT\_CSV: allow users to download CSVs from tables |
| inputParameters | object  Optionall sets default values for input states. The keys are the names of the inputs and the values are the default values for those inputs. |
| expiresIn | number <double>  Default:  "15000"  Optionally specify the expiration time of the embedding url in milliseconds. This represents the maximum allowed time between receiving the API response with the single-use signed URL, and requesting the signed URL for the iframe. Default is 15 seconds. Maximum value is 300 seconds (5 minutes). |
| displayOptions | object  Optionally customize the display of the embedded app |
| testMode | boolean  Run the embed API call in test mode. Does not run the app and will not count towards rate limits or embedding usage counts. |
| property name\* additional property | any |

### Responses

**200**

**400**

**403**

**422**

post/v1/embedding/createPresignedUrl/{projectId}

https://app.company.tech/api/v1/embedding/createPresignedUrl/{projectId}

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "companyUserAttributes": {
  + "orgId": "my-org-id",
  + "groupId": "my-group-id"},
* "scope": [
  + "string"],
* "inputParameters": {
  + "property1": null,
  + "property2": null},
* "expiresIn": "15000",
* "displayOptions": {
  + "theme": "light",
  + "noEmbedHeaderPadding": true,
  + "noEmbedBasePadding": true,
  + "noEmbedOutline": true,
  + "noEmbedFooter": true,
  + "property1": null,
  + "property2": null},
* "testMode": true,
* "property1": null,
* "property2": null

}`

### Response samples

* 200
* 400
* 403
* 422

Content type

application/json

Copy

`{

* "url": "string"

}`

## GetProject

Get metadata about a single project.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### query Parameters

|  |  |
| --- | --- |
| includeSharing | boolean  Default:  false |

### Responses

**200**

**403**

**404**

get/v1/projects/{projectId}

https://app.company.tech/api/v1/projects/{projectId}

### Response samples

* 200
* 403
* 404

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "title": "string",
* "description": "string",
* "type": "PROJECT",
* "creator": {
  + "email": "string"},
* "owner": {
  + "email": "string"},
* "status": {
  + "name": "string"},
* "categories": [
  + {
    - "description": "string",
    - "name": "string"}],
* "reviews": {
  + "required": true},
* "analytics": {
  + "publishedResultsUpdatedAt": "string",
  + "lastViewedAt": "string",
  + "appViews": {
    - "lastThirtyDays": 0,
    - "lastFourteenDays": 0,
    - "lastSevenDays": 0,
    - "allTime": 0}},
* "lastEditedAt": "string",
* "lastPublishedAt": "string",
* "createdAt": "string",
* "archivedAt": "string",
* "trashedAt": "string",
* "schedules": [
  + {
    - "cadence": "HOURLY",
    - "enabled": true,
    - "hourly": {
      * "timezone": "string",
      * "minute": 59},
    - "daily": {
      * "timezone": "string",
      * "minute": 59,
      * "hour": 23},
    - "weekly": {
      * "timezone": "string",
      * "minute": 59,
      * "hour": 23,
      * "dayOfWeek": "SUNDAY"},
    - "monthly": {
      * "timezone": "string",
      * "minute": 59,
      * "hour": 23,
      * "day": 1},
    - "custom": {
      * "timezone": "string",
      * "cron": "string"}}],
* "sharing": {
  + "users": [
    - {
      * "access": "NONE",
      * "user": {
        + "email": "string"}}],
  + "collections": [
    - {
      * "access": "NONE",
      * "collection": {
        + "name": "string"}}],
  + "groups": [
    - {
      * "access": "NONE",
      * "group": {
        + "name": "string"}}],
  + "workspace": {
    - "access": "NONE"},
  + "publicWeb": {
    - "access": "NONE"},
  + "support": {
    - "access": "NONE"}}

}`

## ListProjects

List all viewable projects, sorted by most recently created first.

##### Authorizations:

*bearerAuth*

##### query Parameters

|  |  |
| --- | --- |
| includeArchived | boolean  Default:  false |
| includeComponents | boolean  Default:  false |
| includeTrashed | boolean  Default:  false |
| includeSharing | boolean  Default:  false |
| statuses | Array of strings  Default:  "" |
| categories | Array of strings  Default:  "" |
| creatorEmail | string  Default:  null |
| ownerEmail | string  Default:  null |
| collectionId | string  Default:  null |
| limit | integer <int32>  (PageSize)   [ 1 .. 100 ]  Default:  "25"  Number of results to fetch per page for paginated requests |
| after | any  Default:  null |
| before | any  Default:  null |
| sortBy | string (SortByEnum)  Enum: "CREATED\_AT" "LAST\_EDITED\_AT" "LAST\_PUBLISHED\_AT" |
| sortDirection | string (SortDirectionEnum)  Enum: "DESC" "ASC" |

### Responses

**200**

**400**

**403**

get/v1/projects

https://app.company.tech/api/v1/projects

### Response samples

* 200
* 400
* 403

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "values": [
  + {
    - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    - "title": "string",
    - "description": "string",
    - "type": "PROJECT",
    - "creator": {
      * "email": "string"},
    - "owner": {
      * "email": "string"},
    - "status": {
      * "name": "string"},
    - "categories": [
      * {
        + "description": "string",
        + "name": "string"}],
    - "reviews": {
      * "required": true},
    - "analytics": {
      * "publishedResultsUpdatedAt": "string",
      * "lastViewedAt": "string",
      * "appViews": {
        + "lastThirtyDays": 0,
        + "lastFourteenDays": 0,
        + "lastSevenDays": 0,
        + "allTime": 0}},
    - "lastEditedAt": "string",
    - "lastPublishedAt": "string",
    - "createdAt": "string",
    - "archivedAt": "string",
    - "trashedAt": "string",
    - "schedules": [
      * {
        + "cadence": "HOURLY",
        + "enabled": true,
        + "hourly": {
          - "timezone": "string",
          - "minute": 59},
        + "daily": {
          - "timezone": "string",
          - "minute": 59,
          - "hour": 23},
        + "weekly": {
          - "timezone": "string",
          - "minute": 59,
          - "hour": 23,
          - "dayOfWeek": "SUNDAY"},
        + "monthly": {
          - "timezone": "string",
          - "minute": 59,
          - "hour": 23,
          - "day": 1},
        + "custom": {
          - "timezone": "string",
          - "cron": "string"}}],
    - "sharing": {
      * "users": [
        + {
          - "access": "NONE",
          - "user": {
            * "email": "string"}}],
      * "collections": [
        + {
          - "access": "NONE",
          - "collection": {
            * "name": "string"}}],
      * "groups": [
        + {
          - "access": "NONE",
          - "group": {
            * "name": "string"}}],
      * "workspace": {
        + "access": "NONE"},
      * "publicWeb": {
        + "access": "NONE"},
      * "support": {
        + "access": "NONE"}}}],
* "pagination": {
  + "after": "string",
  + "before": "string"}

}`

## GetQueriedTables

Given a project ID, return the list of warehouse tables queried in the project.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### query Parameters

|  |  |
| --- | --- |
| limit | integer <int32>  (PageSize)   [ 1 .. 100 ]  Default:  "25"  Number of results to fetch per page for paginated requests |
| after | any  Default:  null |
| before | any  Default:  null |

### Responses

**200**

**400**

**403**

**404**

**422**

**500**

get/v1/projects/{projectId}/queriedTables

https://app.company.tech/api/v1/projects/{projectId}/queriedTables

### Response samples

* 200
* 400
* 403
* 404
* 422
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "values": [
  + {
    - "dataConnectionId": "2e0fe5a4-5860-44c6-b0fa-f448a08c1b28",
    - "dataConnectionName": "string",
    - "tableName": "string"}],
* "pagination": {
  + "after": "string",
  + "before": "string"},
* "traceId": "string"

}`

## EditProjectSharingCollections

Add a project to collections or remove it from collections.
Workspace tokens calling this endpoint need to have "Collections -> Write access" scope
in addition to "Projects -> Write access" scope.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing required | object |
| |  |  | | --- | --- | | upsert required | object | | |  |  | | --- | --- | | collections required | Array of objects  <= 25 items | | Array (<= 25 items)  |  |  | | --- | --- | | access required | string (AccessLevelEnum)  Enum: "NONE" "APP\_ONLY" "CAN\_VIEW" "CAN\_EDIT" "FULL\_ACCESS" | | collection required | object | | | | | | |

### Responses

**200**

**400**

**403**

**404**

**500**

patch/v1/projects/{projectId}/sharing/collections

https://app.company.tech/api/v1/projects/{projectId}/sharing/collections

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "upsert": {
    - "collections": [
      * {
        + "access": "NONE",
        + "collection": {
          - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}}

}`

### Response samples

* 200
* 400
* 403
* 404
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "project": {
  + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  + "title": "string",
  + "description": "string",
  + "type": "PROJECT",
  + "creator": {
    - "email": "string"},
  + "owner": {
    - "email": "string"},
  + "status": {
    - "name": "string"},
  + "categories": [
    - {
      * "description": "string",
      * "name": "string"}],
  + "reviews": {
    - "required": true},
  + "analytics": {
    - "publishedResultsUpdatedAt": "string",
    - "lastViewedAt": "string",
    - "appViews": {
      * "lastThirtyDays": 0,
      * "lastFourteenDays": 0,
      * "lastSevenDays": 0,
      * "allTime": 0}},
  + "lastEditedAt": "string",
  + "lastPublishedAt": "string",
  + "createdAt": "string",
  + "archivedAt": "string",
  + "trashedAt": "string",
  + "schedules": [
    - {
      * "cadence": "HOURLY",
      * "enabled": true,
      * "hourly": {
        + "timezone": "string",
        + "minute": 59},
      * "daily": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23},
      * "weekly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "dayOfWeek": "SUNDAY"},
      * "monthly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "day": 1},
      * "custom": {
        + "timezone": "string",
        + "cron": "string"}}],
  + "sharing": {
    - "users": [
      * {
        + "access": "NONE",
        + "user": {
          - "email": "string"}}],
    - "collections": [
      * {
        + "access": "NONE",
        + "collection": {
          - "name": "string"}}],
    - "groups": [
      * {
        + "access": "NONE",
        + "group": {
          - "name": "string"}}],
    - "workspace": {
      * "access": "NONE"},
    - "publicWeb": {
      * "access": "NONE"},
    - "support": {
      * "access": "NONE"}}},
* "errors": [
  + {
    - "collectionIds": [
      * "497f6eca-6276-4993-bfeb-53cbbbba6f08"],
    - "reason": "string"}]

}`

## EditProjectSharingOrgAndPublic

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing required | object |
| |  |  | | --- | --- | | publicWeb | string (PublicWebAccessLevel)  Enum: "NONE" "APP\_ONLY" "CAN\_VIEW" "CAN\_EDIT" "FULL\_ACCESS" | | workspace | string (AccessLevelEnum)  Enum: "NONE" "APP\_ONLY" "CAN\_VIEW" "CAN\_EDIT" "FULL\_ACCESS" | | |

### Responses

**200**

**400**

**403**

**404**

**500**

patch/v1/projects/{projectId}/sharing/workspaceAndPublic

https://app.company.tech/api/v1/projects/{projectId}/sharing/workspaceAndPublic

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "publicWeb": "NONE",
  + "workspace": "NONE"}

}`

### Response samples

* 200
* 400
* 403
* 404
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "project": {
  + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  + "title": "string",
  + "description": "string",
  + "type": "PROJECT",
  + "creator": {
    - "email": "string"},
  + "owner": {
    - "email": "string"},
  + "status": {
    - "name": "string"},
  + "categories": [
    - {
      * "description": "string",
      * "name": "string"}],
  + "reviews": {
    - "required": true},
  + "analytics": {
    - "publishedResultsUpdatedAt": "string",
    - "lastViewedAt": "string",
    - "appViews": {
      * "lastThirtyDays": 0,
      * "lastFourteenDays": 0,
      * "lastSevenDays": 0,
      * "allTime": 0}},
  + "lastEditedAt": "string",
  + "lastPublishedAt": "string",
  + "createdAt": "string",
  + "archivedAt": "string",
  + "trashedAt": "string",
  + "schedules": [
    - {
      * "cadence": "HOURLY",
      * "enabled": true,
      * "hourly": {
        + "timezone": "string",
        + "minute": 59},
      * "daily": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23},
      * "weekly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "dayOfWeek": "SUNDAY"},
      * "monthly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "day": 1},
      * "custom": {
        + "timezone": "string",
        + "cron": "string"}}],
  + "sharing": {
    - "users": [
      * {
        + "access": "NONE",
        + "user": {
          - "email": "string"}}],
    - "collections": [
      * {
        + "access": "NONE",
        + "collection": {
          - "name": "string"}}],
    - "groups": [
      * {
        + "access": "NONE",
        + "group": {
          - "name": "string"}}],
    - "workspace": {
      * "access": "NONE"},
    - "publicWeb": {
      * "access": "NONE"},
    - "support": {
      * "access": "NONE"}}},
* "errors": [
  + {
    - "type": "workspace",
    - "reason": "string"}]

}`

## EditProjectSharingGroups

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing required | object |
| |  |  | | --- | --- | | upsert required | object | | |  |  | | --- | --- | | groups required | Array of objects  <= 25 items | | Array (<= 25 items)  |  |  | | --- | --- | | access required | string (AccessLevelEnum)  Enum: "NONE" "APP\_ONLY" "CAN\_VIEW" "CAN\_EDIT" "FULL\_ACCESS" | | group required | object | | | | | | |

### Responses

**200**

**400**

**403**

**404**

**500**

patch/v1/projects/{projectId}/sharing/groups

https://app.company.tech/api/v1/projects/{projectId}/sharing/groups

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "upsert": {
    - "groups": [
      * {
        + "access": "NONE",
        + "group": {
          - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}}

}`

### Response samples

* 200
* 400
* 403
* 404
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "project": {
  + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  + "title": "string",
  + "description": "string",
  + "type": "PROJECT",
  + "creator": {
    - "email": "string"},
  + "owner": {
    - "email": "string"},
  + "status": {
    - "name": "string"},
  + "categories": [
    - {
      * "description": "string",
      * "name": "string"}],
  + "reviews": {
    - "required": true},
  + "analytics": {
    - "publishedResultsUpdatedAt": "string",
    - "lastViewedAt": "string",
    - "appViews": {
      * "lastThirtyDays": 0,
      * "lastFourteenDays": 0,
      * "lastSevenDays": 0,
      * "allTime": 0}},
  + "lastEditedAt": "string",
  + "lastPublishedAt": "string",
  + "createdAt": "string",
  + "archivedAt": "string",
  + "trashedAt": "string",
  + "schedules": [
    - {
      * "cadence": "HOURLY",
      * "enabled": true,
      * "hourly": {
        + "timezone": "string",
        + "minute": 59},
      * "daily": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23},
      * "weekly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "dayOfWeek": "SUNDAY"},
      * "monthly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "day": 1},
      * "custom": {
        + "timezone": "string",
        + "cron": "string"}}],
  + "sharing": {
    - "users": [
      * {
        + "access": "NONE",
        + "user": {
          - "email": "string"}}],
    - "collections": [
      * {
        + "access": "NONE",
        + "collection": {
          - "name": "string"}}],
    - "groups": [
      * {
        + "access": "NONE",
        + "group": {
          - "name": "string"}}],
    - "workspace": {
      * "access": "NONE"},
    - "publicWeb": {
      * "access": "NONE"},
    - "support": {
      * "access": "NONE"}}},
* "errors": [
  + {
    - "groupIds": [
      * "497f6eca-6276-4993-bfeb-53cbbbba6f08"],
    - "reason": "string"}]

}`

## EditProjectSharingUsers

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing required | object |
| |  |  | | --- | --- | | upsert required | object | | |  |  | | --- | --- | | users required | Array of objects  <= 25 items | | Array (<= 25 items)  |  |  | | --- | --- | | access required | string (AccessLevelEnum)  Enum: "NONE" "APP\_ONLY" "CAN\_VIEW" "CAN\_EDIT" "FULL\_ACCESS" | | user required | object | | | | | | |

### Responses

**200**

**400**

**403**

**404**

**500**

patch/v1/projects/{projectId}/sharing/users

https://app.company.tech/api/v1/projects/{projectId}/sharing/users

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "upsert": {
    - "users": [
      * {
        + "access": "NONE",
        + "user": {
          - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}}

}`

### Response samples

* 200
* 400
* 403
* 404
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "project": {
  + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  + "title": "string",
  + "description": "string",
  + "type": "PROJECT",
  + "creator": {
    - "email": "string"},
  + "owner": {
    - "email": "string"},
  + "status": {
    - "name": "string"},
  + "categories": [
    - {
      * "description": "string",
      * "name": "string"}],
  + "reviews": {
    - "required": true},
  + "analytics": {
    - "publishedResultsUpdatedAt": "string",
    - "lastViewedAt": "string",
    - "appViews": {
      * "lastThirtyDays": 0,
      * "lastFourteenDays": 0,
      * "lastSevenDays": 0,
      * "allTime": 0}},
  + "lastEditedAt": "string",
  + "lastPublishedAt": "string",
  + "createdAt": "string",
  + "archivedAt": "string",
  + "trashedAt": "string",
  + "schedules": [
    - {
      * "cadence": "HOURLY",
      * "enabled": true,
      * "hourly": {
        + "timezone": "string",
        + "minute": 59},
      * "daily": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23},
      * "weekly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "dayOfWeek": "SUNDAY"},
      * "monthly": {
        + "timezone": "string",
        + "minute": 59,
        + "hour": 23,
        + "day": 1},
      * "custom": {
        + "timezone": "string",
        + "cron": "string"}}],
  + "sharing": {
    - "users": [
      * {
        + "access": "NONE",
        + "user": {
          - "email": "string"}}],
    - "collections": [
      * {
        + "access": "NONE",
        + "collection": {
          - "name": "string"}}],
    - "groups": [
      * {
        + "access": "NONE",
        + "group": {
          - "name": "string"}}],
    - "workspace": {
      * "access": "NONE"},
    - "publicWeb": {
      * "access": "NONE"},
    - "support": {
      * "access": "NONE"}}},
* "errors": [
  + {
    - "userIds": [
      * "497f6eca-6276-4993-bfeb-53cbbbba6f08"],
    - "reason": "string"}]

}`

## IngestSemanticProject

Ingest a semantic project from a zip file.

This API endpoint is subject to a maximum of 3 requests per minute.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| semanticProjectId required | string <uuid>  (SemanticProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company semantic project. This can be found from the semantic projects admin panel (in Settings). |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| verbose | boolean  Default:  true  Whether to respond with detail on which components of the semantic layer were successfully synced |
| debug | boolean  Default:  false  Whether to include additional debug information |
| dryRun | boolean  If enabled, the sync will not actually write to the database |

### Responses

**201**

**400**

**403**

**415**

**502**

post/v1/semantic-(projects|models)/{semanticProjectId}/ingest

https://app.company.tech/api/v1/semantic-(projects|models)/{semanticProjectId}/ingest

### Request samples

* Payload

Content type

application/json

Copy

`{

* "verbose": true,
* "debug": false,
* "dryRun": true

}`

### Response samples

* 201
* 400
* 403
* 415
* 502

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "traceId": "string",
* "contents": [
  + "string"],
* "warnings": [
  + "string"],
* "skipped": {
  + "property1": null,
  + "property2": null},
* "problems": [
  + {
    - "severity": "fatal",
    - "message": "string",
    - "cause_paths": [
      * [
        + "string"]],
    - "impact_paths": [
      * [
        + "string"]],
    - "validated_by_json_schema": true,
    - "display": "string"}],
* "debug": {
  + "metricflowModelSchemas": { }}

}`

## RunProject

Trigger a run of the latest published version of a project.

This API endpoint is subject to a maximum of 20 requests per minute and 60 requests per hour.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### header Parameters

|  |  |
| --- | --- |
| flag-config-override | string |

##### Request Body schema: application/json optional

|  |  |
| --- | --- |
| inputParams | object  Optionally specify input parameters for this project run. These should be structured as a dictionary of key/value pairs, where the key name matches the name of the variable in the company project.  Only parameters that are added to the published app can be set via this request parameter. Any additional inputs will be ignored. It is invalid to pass in both a viewId and inputParams.  If no input parameters are provided, the project will be run with the default input values. Note that if input parameters are provided, this run will not be able to update the cached values for the project, and the updateCache setting (below) will be ignored. |
| dryRun | boolean  Default:  "false"  When true, this endpoint will perform a dry run that does not run the project. This can be useful for validating the structure of an API call, and inspecting a dummy response, without running a project. |
| updateCache | boolean  Deprecated |
| notifications | Array of objects (ProjectRunNotification)  Optionally specify a list of notification details that will be delivered once a project run completes. Notifications can be configured for delivery to Slack channels, company users, or company groups. |
| updatePublishedResults | boolean  Default:  "false"  When true, the cached state of the published app will be updated with the latest run results. You must have at least "Can Edit" permissions on the project to do so. Note: this cannot be set to true if custom input parameters are provided. |
| useCachedSqlResults | boolean  Default:  "true"  When false, the project will run without using any cached SQL results, and will update those cached SQL results. |
| viewId | string  Optionally specify a SavedView viewId to use for the project run. If specified, the saved view's inputs will be used for the project run. It is invalid to pass in both a viewId and inputParams. If not specified, the default inputs will be used. |

### Responses

**201**

**400**

**403**

**422**

**503**

post/v1/projects/{projectId}/runs

https://app.company.tech/api/v1/projects/{projectId}/runs

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "inputParams": {
  + "text_input_1": "Hello World",
  + "numeric_input_1": 123},
* "dryRun": "false",
* "updateCache": true,
* "notifications": [
  + {
    - "type": "ALL",
    - "includeSuccessScreenshot": "true",
    - "slackChannelIds": [
      * "C0000000"],
    - "userIds": [
      * "uuid-user-1",
      * "uuid-user-2"]},
  + {
    - "type": "FAILURE",
    - "includeSuccessScreenshot": "false",
    - "userIds": [
      * "uuid-user-1"],
    - "groupIds": [
      * "uuid-group-1"]}],
* "updatePublishedResults": "false",
* "useCachedSqlResults": "true",
* "viewId": "string"

}`

### Response samples

* 201
* 400
* 403
* 422
* 503

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "projectId": "5a8591dd-4039-49df-9202-96385ba3eff8",
* "runId": "78c33d18-170c-44d3-a227-b3194f134f73",
* "runUrl": "string",
* "runStatusUrl": "string",
* "traceId": "string",
* "projectVersion": 0,
* "notifications": [
  + {
    - "type": "SUCCESS",
    - "subject": "string",
    - "body": "string",
    - "recipientType": "USER",
    - "includeSuccessScreenshot": true,
    - "screenshotFormat": [
      * "png"],
    - "recipient": {
      * "id": "C0123456",
      * "name": "data-team",
      * "isPrivate": false}}]

}`

## GetProjectRuns

Get the status of the API-triggered runs of a project.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |

##### query Parameters

|  |  |
| --- | --- |
| limit | integer <int32>  (PageSize)   [ 1 .. 100 ]  Default:  "25"  Number of results to fetch per page for paginated requests |
| offset | integer <int32>  (Offset)   >= 0  Default:  "0"  Offset for paginated requests |
| statusFilter | string (ProjectRunStatus)  Enum: "PENDING" "RUNNING" "ERRORED" "COMPLETED" "KILLED" "UNABLE\_TO\_ALLOCATE\_KERNEL"  Current status of a project run |

### Responses

**200**

**400**

**403**

**422**

get/v1/projects/{projectId}/runs

https://app.company.tech/api/v1/projects/{projectId}/runs

### Response samples

* 200
* 400
* 403
* 422

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "runs": [
  + {
    - "projectId": "5a8591dd-4039-49df-9202-96385ba3eff8",
    - "projectVersion": 0,
    - "runId": "78c33d18-170c-44d3-a227-b3194f134f73",
    - "runUrl": "string",
    - "status": "PENDING",
    - "startTime": "2019-08-24T14:15:22Z",
    - "endTime": "2019-08-24T14:15:22Z",
    - "elapsedTime": 0.1,
    - "flagConfigOverride": "string",
    - "traceId": "string",
    - "notifications": [
      * {
        + "type": "SUCCESS",
        + "subject": "string",
        + "body": "string",
        + "recipientType": "USER",
        + "includeSuccessScreenshot": true,
        + "screenshotFormat": [
          - "png"],
        + "recipient": {
          - "id": "C0123456",
          - "name": "data-team",
          - "isPrivate": false}}],
    - "stateEvents": [
      * {
        + "type": "string",
        + "value": "string",
        + "timestamp": "string"}]}],
* "nextPage": "string",
* "previousPage": "string",
* "traceId": "string"

}`

## GetRunStatus

Get the status of a project run.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |
| runId required | string <uuid>  (InputRunId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a run of a company project. This ID is part of the response returned by the RunProject endpoint. The GetProjectRuns endpoint can also be used to find the specific runs for a project. |

##### header Parameters

|  |  |
| --- | --- |
| enable-expanded-stats | string |

### Responses

**200**

**400**

**403**

**422**

get/v1/projects/{projectId}/runs/{runId}

https://app.company.tech/api/v1/projects/{projectId}/runs/{runId}

### Response samples

* 200
* 400
* 403
* 422

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "projectId": "5a8591dd-4039-49df-9202-96385ba3eff8",
* "projectVersion": 0,
* "runId": "78c33d18-170c-44d3-a227-b3194f134f73",
* "runUrl": "string",
* "status": "PENDING",
* "startTime": "2019-08-24T14:15:22Z",
* "endTime": "2019-08-24T14:15:22Z",
* "elapsedTime": 0.1,
* "flagConfigOverride": "string",
* "traceId": "string",
* "notifications": [
  + {
    - "type": "SUCCESS",
    - "subject": "string",
    - "body": "string",
    - "recipientType": "USER",
    - "includeSuccessScreenshot": true,
    - "screenshotFormat": [
      * "png"],
    - "recipient": {
      * "id": "C0123456",
      * "name": "data-team",
      * "isPrivate": false}}],
* "stateEvents": [
  + {
    - "type": "string",
    - "value": "string",
    - "timestamp": "string"}]

}`

## CancelRun

Cancel a project run.

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| projectId required | string <uuid>  (ProjectId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a company project. This can be found in the Variables side bar of the Logic View of a project, or by visiting the Project, and copying the UUID after `company` in the URL. |
| runId required | string <uuid>  (InputRunId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a run of a company project. This ID is part of the response returned by the RunProject endpoint. The GetProjectRuns endpoint can also be used to find the specific runs for a project. |

### Responses

**204**

**400**

**403**

**422**

delete/v1/projects/{projectId}/runs/{runId}

https://app.company.tech/api/v1/projects/{projectId}/runs/{runId}

### Response samples

* 400
* 403
* 422

Content type

application/json

Copy

`{

* "details": "string",
* "traceId": "string",
* "reason": "string"

}`

## GetGroup

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| groupId required | string <uuid>  (GroupId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a group. This can be found from the groups page (in Settings). |

### Responses

**200**

**400**

**403**

**500**

get/v1/groups/{groupId}

https://app.company.tech/api/v1/groups/{groupId}

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "createdAt": "string"

}`

## DeleteGroup

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| groupId required | string <uuid>  (GroupId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a group. This can be found from the groups page (in Settings). |

### Responses

**200**

**400**

**403**

**500**

delete/v1/groups/{groupId}

https://app.company.tech/api/v1/groups/{groupId}

### Response samples

* 400
* 403
* 500

Content type

application/json

Copy

`{

* "details": "string",
* "traceId": "string",
* "reason": "string"

}`

## EditGroup

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| groupId required | string <uuid>  (GroupId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a group. This can be found from the groups page (in Settings). |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| members | object |
| name | string (Name)   non-empty |

### Responses

**200**

**400**

**403**

**500**

patch/v1/groups/{groupId}

https://app.company.tech/api/v1/groups/{groupId}

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "members": {
  + "remove": {
    - "users": [
      * {
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}]},
  + "add": {
    - "users": [
      * {
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}]}},
* "name": "string"

}`

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "createdAt": "string"

}`

## ListGroups

##### Authorizations:

*bearerAuth*

##### query Parameters

|  |  |
| --- | --- |
| after | any  Default:  null |
| before | any  Default:  null |
| limit | integer <int32>  (LargerPageSize)   [ 1 .. 500 ]  Default:  "25\n\nThis should be used for endpoints where it isn't more expensive to fetch\nmore results."  Number of results to fetch per page for paginated requests |
| sortBy | string (ListGroupsSortByEnum)  Enum: "CREATED\_AT" "NAME" |
| sortDirection | string (SortDirectionEnum)  Enum: "DESC" "ASC" |

### Responses

**200**

**400**

**403**

**500**

get/v1/groups

https://app.company.tech/api/v1/groups

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "values": [
  + {
    - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    - "name": "string",
    - "createdAt": "string"}],
* "pagination": {
  + "after": "string",
  + "before": "string"}

}`

## CreateGroup

##### Authorizations:

*bearerAuth*

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| members | object (GroupMembers) |
| name required | string (Name)   non-empty |

### Responses

**201**

**400**

**403**

**500**

post/v1/groups

https://app.company.tech/api/v1/groups

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "members": {
  + "users": [
    - {
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}]},
* "name": "string"

}`

### Response samples

* 201
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "members": {
  + "users": [
    - {
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}]}

}`

## GetDataConnection

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| dataConnectionId required | string <uuid>  (DataConnectionId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a data connection. |

### Responses

**200**

**400**

**403**

**500**

get/v1/data-connections/{dataConnectionId}

https://app.company.tech/api/v1/data-connections/{dataConnectionId}

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "type": "athena",
* "connectionDetails": {
  + "athena": {
    - "accessKeyId": "string",
    - "workgroup": "string",
    - "catalog": "string",
    - "s3OutputPath": "string",
    - "port": 0.1,
    - "hostname": "string"}},
* "description": "string",
* "connectViaSsh": true,
* "includeMagic": true,
* "allowWritebackCells": true,
* "schemaFilters": {
  + "tables": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "schemas": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "databases": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}}},
* "schemaRefreshSchedule": {
  + "cadence": "HOURLY",
  + "enabled": true,
  + "daily": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23},
  + "weekly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "dayOfWeek": "SUNDAY"},
  + "monthly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "day": 1},
  + "custom": {
    - "timezoneString": "string",
    - "cron": "string"}},
* "schemaRefreshAccess": "ADMINS",
* "sharing": {
  + "workspace": {
    - "public": "NONE",
    - "guests": "NONE",
    - "members": "NONE"},
  + "groups": [
    - {
      * "access": "NONE",
      * "group": {
        + "name": "string",
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}

}`

## EditDataConnection

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| dataConnectionId required | string <uuid>  (DataConnectionId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a data connection. |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing | object |
| schemaRefreshAccess | string (DataConnectionSchemaRefreshAccess)  Enum: "ADMINS" "USERS\_WITH\_QUERY\_ACCESS" |
| schemaRefreshSchedule | object or null |
| schemaFilters | object |
| allowWritebackCells | boolean |
| includeMagic | boolean |
| connectViaSsh | boolean |
| description | string |
| connectionDetails | object or object or object or object or object or object (EditConnectionDetails) |
| name | string |

### Responses

**201**

**400**

**403**

**500**

patch/v1/data-connections/{dataConnectionId}

https://app.company.tech/api/v1/data-connections/{dataConnectionId}

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "workspace": {
    - "public": "NONE",
    - "guests": "NONE",
    - "members": "NONE"},
  + "groups": {
    - "upsert": [
      * {
        + "access": "NONE",
        + "group": {
          - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}},
* "schemaRefreshAccess": "ADMINS",
* "schemaRefreshSchedule": {
  + "cadence": "HOURLY",
  + "enabled": true,
  + "daily": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23},
  + "weekly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "dayOfWeek": "SUNDAY"},
  + "monthly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "day": 1},
  + "custom": {
    - "timezoneString": "string",
    - "cron": "string"}},
* "schemaFilters": {
  + "tables": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "schemas": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "databases": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}}},
* "allowWritebackCells": true,
* "includeMagic": true,
* "connectViaSsh": true,
* "description": "string",
* "connectionDetails": {
  + "athena": {
    - "secretAccessKey": "string",
    - "accessKeyId": "string",
    - "workgroup": "string",
    - "catalog": "string",
    - "s3OutputPath": "string",
    - "port": 0.1,
    - "hostname": "string"}},
* "name": "string"

}`

### Response samples

* 201
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "type": "athena",
* "connectionDetails": {
  + "athena": {
    - "accessKeyId": "string",
    - "workgroup": "string",
    - "catalog": "string",
    - "s3OutputPath": "string",
    - "port": 0.1,
    - "hostname": "string"}},
* "description": "string",
* "connectViaSsh": true,
* "includeMagic": true,
* "allowWritebackCells": true,
* "schemaFilters": {
  + "tables": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "schemas": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "databases": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}}},
* "schemaRefreshSchedule": {
  + "cadence": "HOURLY",
  + "enabled": true,
  + "daily": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23},
  + "weekly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "dayOfWeek": "SUNDAY"},
  + "monthly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "day": 1},
  + "custom": {
    - "timezoneString": "string",
    - "cron": "string"}},
* "schemaRefreshAccess": "ADMINS",
* "sharing": {
  + "workspace": {
    - "public": "NONE",
    - "guests": "NONE",
    - "members": "NONE"},
  + "groups": [
    - {
      * "access": "NONE",
      * "group": {
        + "name": "string",
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}

}`

## ListDataConnections

##### Authorizations:

*bearerAuth*

##### query Parameters

|  |  |
| --- | --- |
| after | any  Default:  null |
| before | any  Default:  null |
| limit | integer <int32>  (PageSize)   [ 1 .. 100 ]  Default:  "25"  Number of results to fetch per page for paginated requests |
| sortBy | string (ListDataConnectionsSortByEnum)  Enum: "CREATED\_AT" "NAME" |
| sortDirection | string (SortDirectionEnum)  Enum: "DESC" "ASC" |

### Responses

**200**

**400**

**403**

**500**

get/v1/data-connections

https://app.company.tech/api/v1/data-connections

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "values": [
  + {
    - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    - "name": "string",
    - "type": "athena",
    - "connectionDetails": {
      * "athena": {
        + "accessKeyId": "string",
        + "workgroup": "string",
        + "catalog": "string",
        + "s3OutputPath": "string",
        + "port": 0.1,
        + "hostname": "string"}},
    - "description": "string",
    - "connectViaSsh": true,
    - "includeMagic": true,
    - "allowWritebackCells": true,
    - "schemaFilters": {
      * "tables": {
        + "exclude": {
          - "values": [
            * "string"],
          - "matchType": "EXACT"},
        + "include": {
          - "values": [
            * "string"],
          - "matchType": "EXACT"}},
      * "schemas": {
        + "exclude": {
          - "values": [
            * "string"],
          - "matchType": "EXACT"},
        + "include": {
          - "values": [
            * "string"],
          - "matchType": "EXACT"}},
      * "databases": {
        + "exclude": {
          - "values": [
            * "string"],
          - "matchType": "EXACT"},
        + "include": {
          - "values": [
            * "string"],
          - "matchType": "EXACT"}}},
    - "schemaRefreshSchedule": {
      * "cadence": "HOURLY",
      * "enabled": true,
      * "daily": {
        + "timezoneString": "string",
        + "minute": 59,
        + "hour": 23},
      * "weekly": {
        + "timezoneString": "string",
        + "minute": 59,
        + "hour": 23,
        + "dayOfWeek": "SUNDAY"},
      * "monthly": {
        + "timezoneString": "string",
        + "minute": 59,
        + "hour": 23,
        + "day": 1},
      * "custom": {
        + "timezoneString": "string",
        + "cron": "string"}},
    - "schemaRefreshAccess": "ADMINS",
    - "sharing": {
      * "workspace": {
        + "public": "NONE",
        + "guests": "NONE",
        + "members": "NONE"},
      * "groups": [
        + {
          - "access": "NONE",
          - "group": {
            * "name": "string",
            * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}}],
* "pagination": {
  + "after": "string",
  + "before": "string"}

}`

## CreateDataConnection

##### Authorizations:

*bearerAuth*

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing | object |
| schemaRefreshAccess | string (DataConnectionSchemaRefreshAccess)  Enum: "ADMINS" "USERS\_WITH\_QUERY\_ACCESS" |
| schemaRefreshSchedule | object (SchemaRefreshScheduleApiResource) |
| schemaFilters | object |
| allowWritebackCells | boolean |
| includeMagic | boolean |
| connectViaSsh | boolean |
| description | string |
| connectionDetails required | object or object or object or object or object or object (CreateConnectionDetails) |
| type required | string (DataConnectionApiType)  Enum: "athena" "bigquery" "databricks" "postgres" "redshift" "snowflake" |
| name required | string (Name)   non-empty |

### Responses

**201**

**400**

**403**

**500**

post/v1/data-connections

https://app.company.tech/api/v1/data-connections

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "workspace": {
    - "public": "NONE",
    - "guests": "NONE",
    - "members": "NONE"},
  + "groups": [
    - {
      * "access": "NONE",
      * "group": {
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]},
* "schemaRefreshAccess": "ADMINS",
* "schemaRefreshSchedule": {
  + "cadence": "HOURLY",
  + "enabled": true,
  + "daily": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23},
  + "weekly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "dayOfWeek": "SUNDAY"},
  + "monthly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "day": 1},
  + "custom": {
    - "timezoneString": "string",
    - "cron": "string"}},
* "schemaFilters": {
  + "tables": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "schemas": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "databases": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}}},
* "allowWritebackCells": true,
* "includeMagic": true,
* "connectViaSsh": true,
* "description": "string",
* "connectionDetails": {
  + "athena": {
    - "secretAccessKey": "string",
    - "accessKeyId": "string",
    - "workgroup": "string",
    - "catalog": "string",
    - "s3OutputPath": "string",
    - "port": 0.1,
    - "hostname": "string"}},
* "type": "athena",
* "name": "string"

}`

### Response samples

* 201
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "type": "athena",
* "connectionDetails": {
  + "athena": {
    - "accessKeyId": "string",
    - "workgroup": "string",
    - "catalog": "string",
    - "s3OutputPath": "string",
    - "port": 0.1,
    - "hostname": "string"}},
* "description": "string",
* "connectViaSsh": true,
* "includeMagic": true,
* "allowWritebackCells": true,
* "schemaFilters": {
  + "tables": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "schemas": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}},
  + "databases": {
    - "exclude": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"},
    - "include": {
      * "values": [
        + "string"],
      * "matchType": "EXACT"}}},
* "schemaRefreshSchedule": {
  + "cadence": "HOURLY",
  + "enabled": true,
  + "daily": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23},
  + "weekly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "dayOfWeek": "SUNDAY"},
  + "monthly": {
    - "timezoneString": "string",
    - "minute": 59,
    - "hour": 23,
    - "day": 1},
  + "custom": {
    - "timezoneString": "string",
    - "cron": "string"}},
* "schemaRefreshAccess": "ADMINS",
* "sharing": {
  + "workspace": {
    - "public": "NONE",
    - "guests": "NONE",
    - "members": "NONE"},
  + "groups": [
    - {
      * "access": "NONE",
      * "group": {
        + "name": "string",
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}}]}

}`

## ListUsers

##### Authorizations:

*bearerAuth*

##### query Parameters

|  |  |
| --- | --- |
| after | any  Default:  null |
| before | any  Default:  null |
| limit | integer <int32>  (LargerPageSize)   [ 1 .. 500 ]  Default:  "25\n\nThis should be used for endpoints where it isn't more expensive to fetch\nmore results."  Number of results to fetch per page for paginated requests |
| sortBy | string (ListUsersSortByEnum)  Enum: "NAME" "EMAIL" |
| sortDirection | string (SortDirectionEnum)  Enum: "DESC" "ASC" |
| groupId | any  Default:  null |

### Responses

**200**

**400**

**403**

**500**

get/v1/users

https://app.company.tech/api/v1/users

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "values": [
  + {
    - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    - "name": "string",
    - "role": "ADMIN",
    - "email": "string"}],
* "pagination": {
  + "after": "string",
  + "before": "string"}

}`

## DeactivateUser

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| userId required | string <uuid>  (UserId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a user. This can be found from the users page (in Settings). |

### Responses

**200**

**400**

**403**

**500**

post/v1/users/{userId}/deactivate

https://app.company.tech/api/v1/users/{userId}/deactivate

### Response samples

* 400
* 403
* 500

Content type

application/json

Copy

`{

* "details": "string",
* "traceId": "string",
* "reason": "string"

}`

## GetCollection

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| collectionId required | string <uuid>  (CollectionId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a collection. |

### Responses

**200**

**400**

**403**

**500**

get/v1/collections/{collectionId}

https://app.company.tech/api/v1/collections/{collectionId}

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "description": "string",
* "creator": {
  + "email": "string",
  + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"},
* "sharing": {
  + "users": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "groups": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "workspace": {
    - "members": "string"}}

}`

## EditCollection

##### Authorizations:

*bearerAuth*

##### path Parameters

|  |  |
| --- | --- |
| collectionId required | string <uuid>  (CollectionId) ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}...Show pattern  Unique ID for a collection. |

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing | object |
| description | string |
| name | string (Name)   non-empty |

### Responses

**200**

**400**

**403**

**500**

patch/v1/collections/{collectionId}

https://app.company.tech/api/v1/collections/{collectionId}

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "upsert": {
    - "users": [
      * {
        + "access": "string",
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
    - "groups": [
      * {
        + "access": "string",
        + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
    - "workspace": {
      * "members": "string"}}},
* "description": "string",
* "name": "string"

}`

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "description": "string",
* "creator": {
  + "email": "string",
  + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"},
* "sharing": {
  + "users": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "groups": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "workspace": {
    - "members": "string"}}

}`

## ListCollections

##### Authorizations:

*bearerAuth*

##### query Parameters

|  |  |
| --- | --- |
| after | any  Default:  null |
| before | any  Default:  null |
| limit | integer <int32>  (PageSize)   [ 1 .. 100 ]  Default:  "25"  Number of results to fetch per page for paginated requests |
| sortBy | string (ListCollectionsSortByEnum)  Value: "NAME" |

### Responses

**200**

**400**

**403**

**500**

get/v1/collections

https://app.company.tech/api/v1/collections

### Response samples

* 200
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "values": [
  + {
    - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    - "name": "string",
    - "description": "string",
    - "creator": {
      * "email": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"},
    - "sharing": {
      * "users": [
        + {
          - "access": "string",
          - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
      * "groups": [
        + {
          - "access": "string",
          - "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
      * "workspace": {
        + "members": "string"}}}],
* "pagination": {
  + "after": "string",
  + "before": "string"}

}`

## CreateCollection

##### Authorizations:

*bearerAuth*

##### Request Body schema: application/json required

|  |  |
| --- | --- |
| sharing | object (CollectionApiResourceSharing) |
| description | string |
| name required | string |

### Responses

**201**

**400**

**403**

**500**

post/v1/collections

https://app.company.tech/api/v1/collections

### Request samples

* Payload

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "sharing": {
  + "users": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "groups": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "workspace": {
    - "members": "string"}},
* "description": "string",
* "name": "string"

}`

### Response samples

* 201
* 400
* 403
* 500

Content type

application/json

Copy

 Expand all  Collapse all

`{

* "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
* "name": "string",
* "description": "string",
* "creator": {
  + "email": "string",
  + "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"},
* "sharing": {
  + "users": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "groups": [
    - {
      * "access": "string",
      * "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"}],
  + "workspace": {
    - "members": "string"}}

}`

[Previous

API overview](api-overview.md)[Next

Trust](../trust.md)

* [Docs](../index.md)
* [Gallery](https://company.tech/gallery)

* [Sign up](https://app.company.tech/signup)
* [Careers](https://company.tech/jobs)
* [Blog](https://company.tech/blog)
* [Security](https://company.tech/security)
* [Changelog](/changelog)

Copyright © 2025 company Technologies Inc.