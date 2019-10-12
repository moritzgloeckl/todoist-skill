import re
import datetime
from .todoist_wrapper import TodoistWrapper

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_file_handler, intent_handler
from mycroft.util.log import LOG
from mycroft.util.parse import extract_datetime
from mycroft.util.format import nice_date
from mycroft.api import DeviceApi

import httplib2
from oauth2client import client
from requests import HTTPError


class MycroftTokenCredentials(client.AccessTokenCredentials):
    def __init__(self, cred_id):
        self.cred_id = cred_id
        d = self.get_credentials()
        super(MycroftTokenCredentials, self).__init__(d['access_token'], d['user_agent'])

    def get_credentials(self):
        """
        Get credentials through backend. Will do a single retry for
        if an HTTPError occurs.
        Returns: dict with data received from backend
        """
        retry = False
        try:
            d = DeviceApi().get_oauth_token(self.cred_id)
        except HTTPError:
            retry = True
        if retry:
            d = DeviceApi().get_oauth_token(self.cred_id)
        return d

    def _refresh(self, http):
        """
        Override to handle refresh through mycroft backend.
        """
        d = self.get_credentials()
        self.access_token = d['access_token']


class TodoistSkill(MycroftSkill):
    PROJECT_REGEX = "(the|my)(.*)(todo|to do|to-do)"

    def __init__(self):
        MycroftSkill.__init__(self)
        self.settings.set_changed_callback(self._setup_api)
        self._setup_api()

    def _setup_api(self):
        token = str(self.settings.get('ApiKey', '')) or self._setup_oauth()
        if token:
            self.todoist = TodoistWrapper(token)
        else:
            LOG.error("No API key")
            #self.speak_dialog("SetupFirst")

    def _setup_oauth(self):
        try:
            self.credentials = MycroftTokenCredentials(4)
            http = self.credentials.authorize(httplib2.Http())
            return http.request.credentials.access_token
        except HTTPError:
            return None

    @intent_handler(IntentBuilder("ReadTasksIntent").require("ReadTaskKeyword").require("TodoKeyword"))
    def handle_read_tasks_intent(self, message):
        time = extract_datetime(message.data.get("utterance", ""))[0]
        project = self._extract_project(message.data.get("utterance", ""))

        tasks = self.todoist.get_tasks(time=time, project_name=project)

        if len(tasks) > 0:
            if not self.todoist.project_exists(project):
                project = ""
            self.speak_dialog('TasksOnTodo',
                              data={'project': project, 'datetime': nice_date(time, now=datetime.datetime.now())})
            for task in tasks:
                self.speak(task)
        else:
            self.speak_dialog('NoTasks',
                              data={'project': project or "", 'datetime': nice_date(time, now=datetime.datetime.now())})

    @intent_file_handler('AddTask.intent')
    def handle_add_task_intent(self, message):
        self.todoist.add_task(message.data.get('task'), message.data.get('datetime', 'today'),
                              message.data.get('project', ''))
        self.speak_dialog('ConfirmAdd',
                          data={'task': message.data.get('task'), 'project': message.data.get('project', ''),
                                'datetime': message.data.get('datetime', 'today')})

    @intent_file_handler('CompleteTask.intent')
    def handle_complete_task_intent(self, message):
        if self.todoist.complete_task(message.data.get('task')):
            self.speak_dialog('ConfirmComplete', data={'task': message.data.get('task')})
        else:
            self.speak_dialog('ErrorComplete', data={'task': message.data.get('task')})

    def _extract_project(self, string):
        result = re.search(self.PROJECT_REGEX, string)
        return result.group(2).strip() or None


def create_skill():
    return TodoistSkill()
