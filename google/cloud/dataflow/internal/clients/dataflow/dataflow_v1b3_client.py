"""Generated client library for dataflow version v1b3."""
# NOTE: This file is autogenerated and should not be edited by hand.
from apitools.base.py import base_api
from google.cloud.dataflow.internal.clients.dataflow import dataflow_v1b3_messages as messages


class DataflowV1b3(base_api.BaseApiClient):
  """Generated client library for service dataflow version v1b3."""

  MESSAGES_MODULE = messages

  _PACKAGE = u'dataflow'
  _SCOPES = [u'https://www.googleapis.com/auth/cloud-platform', u'https://www.googleapis.com/auth/userinfo.email']
  _VERSION = u'v1b3'
  _CLIENT_ID = '1042881264118.apps.googleusercontent.com'
  _CLIENT_SECRET = 'x_Tw5K8nnjoRAqULM9PFAC2b'
  _USER_AGENT = 'x_Tw5K8nnjoRAqULM9PFAC2b'
  _CLIENT_CLASS_NAME = u'DataflowV1b3'
  _URL_VERSION = u'v1b3'
  _API_KEY = None

  def __init__(self, url='', credentials=None,
               get_credentials=True, http=None, model=None,
               log_request=False, log_response=False,
               credentials_args=None, default_global_params=None,
               additional_http_headers=None):
    """Create a new dataflow handle."""
    url = url or u'https://dataflow.googleapis.com/'
    super(DataflowV1b3, self).__init__(
        url, credentials=credentials,
        get_credentials=get_credentials, http=http, model=model,
        log_request=log_request, log_response=log_response,
        credentials_args=credentials_args,
        default_global_params=default_global_params,
        additional_http_headers=additional_http_headers)
    self.projects_jobs_messages = self.ProjectsJobsMessagesService(self)
    self.projects_jobs_workItems = self.ProjectsJobsWorkItemsService(self)
    self.projects_jobs = self.ProjectsJobsService(self)
    self.projects = self.ProjectsService(self)

  class ProjectsJobsMessagesService(base_api.BaseApiService):
    """Service class for the projects_jobs_messages resource."""

    _NAME = u'projects_jobs_messages'

    def __init__(self, client):
      super(DataflowV1b3.ProjectsJobsMessagesService, self).__init__(client)
      self._method_configs = {
          'List': base_api.ApiMethodInfo(
              http_method=u'GET',
              method_id=u'dataflow.projects.jobs.messages.list',
              ordered_params=[u'projectId', u'jobId'],
              path_params=[u'jobId', u'projectId'],
              query_params=[u'endTime', u'minimumImportance', u'pageSize', u'pageToken', u'startTime'],
              relative_path=u'v1b3/projects/{projectId}/jobs/{jobId}/messages',
              request_field='',
              request_type_name=u'DataflowProjectsJobsMessagesListRequest',
              response_type_name=u'ListJobMessagesResponse',
              supports_download=False,
          ),
          }

      self._upload_configs = {
          }

    def List(self, request, global_params=None):
      """Request the job status.

      Args:
        request: (DataflowProjectsJobsMessagesListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ListJobMessagesResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

  class ProjectsJobsWorkItemsService(base_api.BaseApiService):
    """Service class for the projects_jobs_workItems resource."""

    _NAME = u'projects_jobs_workItems'

    def __init__(self, client):
      super(DataflowV1b3.ProjectsJobsWorkItemsService, self).__init__(client)
      self._method_configs = {
          'Lease': base_api.ApiMethodInfo(
              http_method=u'POST',
              method_id=u'dataflow.projects.jobs.workItems.lease',
              ordered_params=[u'projectId', u'jobId'],
              path_params=[u'jobId', u'projectId'],
              query_params=[],
              relative_path=u'v1b3/projects/{projectId}/jobs/{jobId}/workItems:lease',
              request_field=u'leaseWorkItemRequest',
              request_type_name=u'DataflowProjectsJobsWorkItemsLeaseRequest',
              response_type_name=u'LeaseWorkItemResponse',
              supports_download=False,
          ),
          'ReportStatus': base_api.ApiMethodInfo(
              http_method=u'POST',
              method_id=u'dataflow.projects.jobs.workItems.reportStatus',
              ordered_params=[u'projectId', u'jobId'],
              path_params=[u'jobId', u'projectId'],
              query_params=[],
              relative_path=u'v1b3/projects/{projectId}/jobs/{jobId}/workItems:reportStatus',
              request_field=u'reportWorkItemStatusRequest',
              request_type_name=u'DataflowProjectsJobsWorkItemsReportStatusRequest',
              response_type_name=u'ReportWorkItemStatusResponse',
              supports_download=False,
          ),
          }

      self._upload_configs = {
          }

    def Lease(self, request, global_params=None):
      """Leases a dataflow WorkItem to run.

      Args:
        request: (DataflowProjectsJobsWorkItemsLeaseRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (LeaseWorkItemResponse) The response message.
      """
      config = self.GetMethodConfig('Lease')
      return self._RunMethod(
          config, request, global_params=global_params)

    def ReportStatus(self, request, global_params=None):
      """Reports the status of dataflow WorkItems leased by a worker.

      Args:
        request: (DataflowProjectsJobsWorkItemsReportStatusRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ReportWorkItemStatusResponse) The response message.
      """
      config = self.GetMethodConfig('ReportStatus')
      return self._RunMethod(
          config, request, global_params=global_params)

  class ProjectsJobsService(base_api.BaseApiService):
    """Service class for the projects_jobs resource."""

    _NAME = u'projects_jobs'

    def __init__(self, client):
      super(DataflowV1b3.ProjectsJobsService, self).__init__(client)
      self._method_configs = {
          'Create': base_api.ApiMethodInfo(
              http_method=u'POST',
              method_id=u'dataflow.projects.jobs.create',
              ordered_params=[u'projectId'],
              path_params=[u'projectId'],
              query_params=[u'replaceJobId', u'view'],
              relative_path=u'v1b3/projects/{projectId}/jobs',
              request_field=u'job',
              request_type_name=u'DataflowProjectsJobsCreateRequest',
              response_type_name=u'Job',
              supports_download=False,
          ),
          'Get': base_api.ApiMethodInfo(
              http_method=u'GET',
              method_id=u'dataflow.projects.jobs.get',
              ordered_params=[u'projectId', u'jobId'],
              path_params=[u'jobId', u'projectId'],
              query_params=[u'view'],
              relative_path=u'v1b3/projects/{projectId}/jobs/{jobId}',
              request_field='',
              request_type_name=u'DataflowProjectsJobsGetRequest',
              response_type_name=u'Job',
              supports_download=False,
          ),
          'GetMetrics': base_api.ApiMethodInfo(
              http_method=u'GET',
              method_id=u'dataflow.projects.jobs.getMetrics',
              ordered_params=[u'projectId', u'jobId'],
              path_params=[u'jobId', u'projectId'],
              query_params=[u'startTime'],
              relative_path=u'v1b3/projects/{projectId}/jobs/{jobId}/metrics',
              request_field='',
              request_type_name=u'DataflowProjectsJobsGetMetricsRequest',
              response_type_name=u'JobMetrics',
              supports_download=False,
          ),
          'List': base_api.ApiMethodInfo(
              http_method=u'GET',
              method_id=u'dataflow.projects.jobs.list',
              ordered_params=[u'projectId'],
              path_params=[u'projectId'],
              query_params=[u'filter', u'pageSize', u'pageToken', u'view'],
              relative_path=u'v1b3/projects/{projectId}/jobs',
              request_field='',
              request_type_name=u'DataflowProjectsJobsListRequest',
              response_type_name=u'ListJobsResponse',
              supports_download=False,
          ),
          'Update': base_api.ApiMethodInfo(
              http_method=u'PUT',
              method_id=u'dataflow.projects.jobs.update',
              ordered_params=[u'projectId', u'jobId'],
              path_params=[u'jobId', u'projectId'],
              query_params=[],
              relative_path=u'v1b3/projects/{projectId}/jobs/{jobId}',
              request_field=u'job',
              request_type_name=u'DataflowProjectsJobsUpdateRequest',
              response_type_name=u'Job',
              supports_download=False,
          ),
          }

      self._upload_configs = {
          }

    def Create(self, request, global_params=None):
      """Creates a dataflow job.

      Args:
        request: (DataflowProjectsJobsCreateRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Job) The response message.
      """
      config = self.GetMethodConfig('Create')
      return self._RunMethod(
          config, request, global_params=global_params)

    def Get(self, request, global_params=None):
      """Gets the state of the specified dataflow job.

      Args:
        request: (DataflowProjectsJobsGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Job) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    def GetMetrics(self, request, global_params=None):
      """Request the job status.

      Args:
        request: (DataflowProjectsJobsGetMetricsRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (JobMetrics) The response message.
      """
      config = self.GetMethodConfig('GetMetrics')
      return self._RunMethod(
          config, request, global_params=global_params)

    def List(self, request, global_params=None):
      """List the jobs of a project.

      Args:
        request: (DataflowProjectsJobsListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ListJobsResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    def Update(self, request, global_params=None):
      """Updates the state of an existing dataflow job.

      Args:
        request: (DataflowProjectsJobsUpdateRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Job) The response message.
      """
      config = self.GetMethodConfig('Update')
      return self._RunMethod(
          config, request, global_params=global_params)

  class ProjectsService(base_api.BaseApiService):
    """Service class for the projects resource."""

    _NAME = u'projects'

    def __init__(self, client):
      super(DataflowV1b3.ProjectsService, self).__init__(client)
      self._method_configs = {
          'WorkerMessages': base_api.ApiMethodInfo(
              http_method=u'POST',
              method_id=u'dataflow.projects.workerMessages',
              ordered_params=[u'projectId'],
              path_params=[u'projectId'],
              query_params=[],
              relative_path=u'v1b3/projects/{projectId}/WorkerMessages',
              request_field=u'sendWorkerMessagesRequest',
              request_type_name=u'DataflowProjectsWorkerMessagesRequest',
              response_type_name=u'SendWorkerMessagesResponse',
              supports_download=False,
          ),
          }

      self._upload_configs = {
          }

    def WorkerMessages(self, request, global_params=None):
      """Send a worker_message to the service.

      Args:
        request: (DataflowProjectsWorkerMessagesRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (SendWorkerMessagesResponse) The response message.
      """
      config = self.GetMethodConfig('WorkerMessages')
      return self._RunMethod(
          config, request, global_params=global_params)
