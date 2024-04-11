# -*- coding: utf-8 -*-
"""
Manager for data validation processes.
"""

import typing

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFeedback,
    QgsProject,
    QgsPrintLayout,
    QgsTask,
)

from qgis.PyQt import QtCore, QtGui

from ...models.base import NcsPathway
from ...models.validation import SubmitResult, ValidationResult
from ...utils import FileUtils, log, tr
from .validators import NcsDataValidator


class ValidationManager(QtCore.QObject):
    """Manages the validation process including starting, cancelling
    or getting the status of running validation tasks.
    """

    validation_started = QtCore.pyqtSignal(str)
    validation_error = QtCore.pyqtSignal(str)
    validation_completed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Data validator (value) indexed by task id (key)
        self._validation_tasks = {}

        # Validation results (value) indexed by task id (key)
        self._validation_results = {}

        self.task_manager = QgsApplication.instance().taskManager()
        self.task_manager.statusChanged.connect(self.on_task_status_changed)

    def validate_ncs_pathways(
        self, pathways: typing.List[NcsPathway], cancel_running=True
    ) -> SubmitResult:
        """Validates a set of NcsPathway datasets and returns the status
        of the submission.

        :param pathways: A list of NcsPathway objects to be validated. More than one
        NcsPathway is required for the validation process to be executed.
        :type pathways: list

        :param cancel_running: True if any running validation processes are to be cancelled
        else False if multiple concurrent validation processes are to be executed.
        :type cancel_running: bool

        :returns: Result object containing the task id and status of the submission.
        :rtype: SubmitResult
        """
        if len(pathways) < 2:
            return SubmitResult("", False)

        if cancel_running:
            self.cancel_ncs_validation()

        ncs_validator = NcsDataValidator()
        ncs_validator.model_components = pathways
        task_id = self.task_manager.addTask(NcsDataValidator)

        if task_id == 0:
            return SubmitResult("", False)

        self._validation_tasks[str(task_id)] = ncs_validator

        return SubmitResult(str(task_id), True)

    def cancel_ncs_validation(self):
        """Cancel all validation processes of NCS pathway datasets."""
        for task_id in list(self._validation_tasks):
            ncs_validator = self._validation_tasks[task_id]
            status = ncs_validator.status()
            if (
                status == QgsTask.TaskStatus.Running
                or status == QgsTask.TaskStatus.Queued
                or status == QgsTask.TaskStatus.OnHold
            ):
                ncs_validator.cancel()
                del self._validation_tasks[task_id]

                if task_id in self._validation_results:
                    del self._validation_results[task_id]

    def on_validation_status_changed(self, task_id: int, status: QgsTask.TaskStatus):
        """Slot raised when the status of a validation task has changed.

        This function will emit when the validation task has started, when it
        has completed successfully or terminated due to an error.

        :param task_id: ID of the task.
        :type task_id: int

        :param status: New task status.
        :type status: QgsTask.TaskStatus
        """
        if status == QgsTask.TaskStatus.Running:
            self.validation_started.emit(str(task_id))

        elif status == QgsTask.TaskStatus.Complete:
            if str(task_id) not in self._validation_tasks:
                return

            # Get result
            validator = self.task_manager.task(task_id)
            result = validator.result
            if result is not None:
                self._validation_results[str(task_id)] = result

            # Remove task
            if str(task_id) in self._validation_tasks:
                del self._validation_tasks[str(task_id)]

            self.validation_completed.emit(str(task_id))

    def ncs_result(self) -> ValidationResult:
        """Gets the result of the last successful validation of NCS pathways.

        :returns: Result of the last successful NCS pathway validation.
        :rtype: ValidationResult
        """
        pass



validation_manager = ValidationManager()
