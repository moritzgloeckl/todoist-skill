import todoist


class TodoistWrapper:

    def __init__(self, api_key):
        self.api = todoist.TodoistAPI(api_key)
        self.api.sync()

    def add_task(self, content, time=None, project_name=None):
        self.api.sync()
        task = self.api.items.add(content)

        task.update(due={'string': time})

        if project_name:
            project = next(
                filter(lambda project: project['name'].lower() == project_name.lower(), self.api.state['projects']),
                None)
            if project:
                task.move(project_id=project["id"])

        self.api.commit()

    def get_tasks(self, time=None, project_name=None):
        self.api.sync()
        tasks = self._get_all_active_tasks()

        if project_name:
            project = next(
                filter(lambda project: project['name'].lower() == project_name.lower(), self.api.state['projects']),
                None)
            if project:
                tasks = list(filter(lambda task: task['project_id'] == project['id'], tasks))

        # Filter tasks by time
        tasks = list(filter(lambda task: task['due']['date'] == time.strftime("%Y-%m-%d"), tasks))

        # Transform tasks object array to string list
        tasks = list(map(lambda task: task['content'], tasks))

        return tasks

    def complete_task(self, content):
        self.api.sync()
        task = next(filter(lambda task: task['content'] == content, self.api.state['items']), None)
        if task:
            task.complete()
            self.api.commit()
            return True
        else:
            return False

    def project_exists(self, project_name):
        if not project_name:
            return False
        return next(filter(lambda project: project['name'].lower() == project_name.lower(), self.api.state['projects']),
                    None) is not None

    def _get_all_active_tasks(self):
        return list(filter(lambda task: self._is_task_active(task), self.api.state['items']))

    def _is_task_active(self, task):
        result = True
        try:
            result = result and task['content'] is not None \
                     and task['is_deleted'] == 0 \
                     and task['in_history'] == 0
            return result
        except KeyError:
            return False
