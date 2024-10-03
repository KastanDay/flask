"""
Convert all Supabase queries to SQLAlchemy queries.
"""
import logging
from typing import List

from flask_sqlalchemy import SQLAlchemy
from injector import inject

import ai_ta_backend.model.models as models
from ai_ta_backend.model.response import DatabaseResponse

class SQLAlchemyDatabase:

    @inject
    def __init__(self, db: SQLAlchemy):
        logging.info("Initializing SQLAlchemyDatabase")
        self.db = db
    
    # Document-related queries

    def getAllMaterialsForCourse(self, course_name: str):
        try:
            query = self.db.select(models.Document).where(models.Document.course_name == course_name)
            result = self.db.session.execute(query).scalars().all()
            documents: List[models.Document] = [doc for doc in result]
            return DatabaseResponse[models.Document](data=documents, count=len(result))
        finally:
            self.db.session.close()
    
    def getMaterialsForCourseAndS3Path(self, course_name: str, s3_path: str):
        try:
            query = self.db.select(models.Document).where(models.Document.course_name == course_name, models.Document.s3_path == s3_path)
            result = self.db.session.execute(query).scalars().all()
            documents: List[models.Document] = [doc for doc in result]
            return DatabaseResponse[models.Document](data=documents, count=len(result))
        finally:
            self.db.session.close()
    
    def getMaterialsForCourseAndKeyAndValue(self, course_name: str, key: str, value: str):
        try:
            query = self.db.select(models.Document).where(models.Document.course_name == course_name, getattr(models.Document, key) == value)
            result = self.db.session.execute(query).scalars().all()
            documents: List[models.Document] = [doc for doc in result]
            return DatabaseResponse[models.Document](data=documents, count=len(result))
        finally:
            self.db.session.close()
    
    def deleteMaterialsForCourseAndKeyAndValue(self, course_name: str, key: str, value: str):
        try:
            query = self.db.delete(models.Document).where(models.Document.course_name == course_name, getattr(models.Document, key) == value)
            self.db.session.execute(query)
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    def deleteMaterialsForCourseAndS3Path(self, course_name: str, s3_path: str):
        try:
            query = self.db.delete(models.Document).where(models.Document.course_name == course_name, models.Document.s3_path == s3_path)
            self.db.session.execute(query)
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    def getDocumentsBetweenDates(self, course_name: str, from_date: str, to_date: str, table_name: str):
        try:
            query = self.db.select(models.Document).where(models.Document.course_name == course_name)
            if from_date:
                query = query.filter(models.Document.created_at >= from_date)
            if to_date:
                query = query.filter(models.Document.created_at <= to_date)
            result = self.db.session.execute(query).scalars().all()
            documents: List[models.Document] = [doc for doc in result]
            return DatabaseResponse[models.Document](data=documents, count=len(result))
        finally:
            self.db.session.close()

    def getAllDocumentsForDownload(self, course_name: str, first_id: int):
        try:
            query = self.db.select(models.Document).where(models.Document.course_name == course_name, models.Document.id >= first_id)
            result = self.db.session.execute(query).scalars().all()
            documents: List[models.Document] = [doc for doc in result]
            return DatabaseResponse[models.Document](data=documents, count=len(result))
        finally:
            self.db.session.close()
    
    def getDocsForIdsGte(self, course_name: str, first_id: int, fields: str = "*", limit: int = 100):
        try:
            fields_to_select = [getattr(models.Document, field) for field in fields.split(", ")]    
            query = self.db.select(*fields_to_select).where(models.Document.course_name == course_name, models.Document.id >= first_id).limit(limit)
            result = self.db.session.execute(query).scalars().all()
            documents: List[models.Document] = [doc for doc in result]
            return DatabaseResponse[models.Document](data=documents, count=len(result))
        finally:
            self.db.session.close()
    
    # Project-related queries

    def getProjectsMapForCourse(self, course_name: str):
        try:
            query = self.db.select(models.Project.doc_map_id).where(models.Project.course_name == course_name)
            result = self.db.session.execute(query).scalars().all()
            projects: List[models.Project] = [project for project in result]
            return DatabaseResponse[models.Project](data=projects, count=len(result))
        finally:
            self.db.session.close()
    
    def insertProjectInfo(self, project_info):
        try:
            self.db.session.execute(self.db.insert(models.Project).values(**project_info))
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    def getDocMapFromProjects(self, course_name: str):
        try:
            query = self.db.select(models.Project.doc_map_id).where(models.Project.course_name == course_name)
            result = self.db.session.execute(query).scalars().all()
            projects: List[models.Project] = [project for project in result]
            return DatabaseResponse[models.Project](data=projects, count=len(result))
        finally:
            self.db.session.close()
    
    def getConvoMapFromProjects(self, course_name: str):
        try:
            query = self.db.select(models.Project).where(models.Project.course_name == course_name)
            result = self.db.session.execute(query).scalars().all()
            projects: List[models.Project] = [project for project in result]
            return DatabaseResponse[models.Project](data=projects, count=len(result))
        finally:
            self.db.session.close()
    
    def updateProjects(self, course_name: str, data: dict):
        try:
            query = self.db.update(models.Project).where(models.Project.course_name == course_name).values(**data)
            self.db.session.execute(query)
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    def insertProject(self, project_info):
        try:
            self.db.session.execute(self.db.insert(models.Project).values(**project_info))
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    # Conversation-related queries

    def getAllConversationsForDownload(self, course_name: str, first_id: int):
        try:
            query = self.db.select(models.LlmConvoMonitor).where(models.LlmConvoMonitor.course_name == course_name, models.LlmConvoMonitor.id >= first_id)
            result = self.db.session.execute(query).scalars().all()
            conversations: List[models.LlmConvoMonitor] = [convo for convo in result]
            return DatabaseResponse[models.LlmConvoMonitor](data=conversations, count=len(result))
        finally:
            self.db.session.close()
    
    def getAllConversationsBetweenIds(self, course_name: str, first_id: int, last_id: int, limit: int = 50):
        try:
            query = self.db.select(models.LlmConvoMonitor).where(models.LlmConvoMonitor.course_name == course_name, models.LlmConvoMonitor.id > first_id)
            if last_id != 0:
                query = query.filter(models.LlmConvoMonitor.id <= last_id)
            query = query.limit(limit)
            result = self.db.session.execute(query).scalars().all()
            conversations: List[models.LlmConvoMonitor] = [doc for doc in result]
            return DatabaseResponse[models.LlmConvoMonitor](data=conversations, count=len(result))
        finally:
            self.db.session.close()
    
    def getAllFromLLMConvoMonitor(self, course_name: str):
        try:
            query = self.db.select(models.LlmConvoMonitor).where(models.LlmConvoMonitor.course_name == course_name)
            result = self.db.session.execute(query).scalars().all()
            conversations: List[models.LlmConvoMonitor] = [convo for convo in result]
            return DatabaseResponse[models.LlmConvoMonitor](data=conversations, count=len(result))
        finally:
            self.db.session.close()
    
    def getCountFromLLMConvoMonitor(self, course_name: str, last_id: int):
        try:
            query = self.db.select(models.LlmConvoMonitor.id).where(models.LlmConvoMonitor.course_name == course_name)
            if last_id != 0:
                query = query.filter(models.LlmConvoMonitor.id > last_id)
            count_query = self.db.select(self.db.func.count()).select_from(query.subquery())
            self.db.session.execute(count_query).scalar()
            return DatabaseResponse[models.LlmConvoMonitor](data=[], count=1)
        finally:
            self.db.session.close()
    
    def getConversation(self, course_name: str, key: str, value: str):
        try:
            query = self.db.select(models.LlmConvoMonitor).where(getattr(models.LlmConvoMonitor, key) == value, models.LlmConvoMonitor.course_name == course_name)
            result = self.db.session.execute(query).scalars().all()
            conversations: List[models.LlmConvoMonitor] = [convo for convo in result]
            return DatabaseResponse[models.LlmConvoMonitor](data=conversations, count=len(result))
        finally:
            self.db.session.close()
    
    def getAllConversationsForUserAndProject(self, user_email: str, project_name: str, curr_count: int = 0):
        try:
            messages_subquery = (
                self.db.session.query(
                    models.Messages.content_text,
                    models.Messages.content_image_url,
                    models.Messages.role,
                    models.Messages.image_description,
                    models.Messages.created_at
                )
                .order_by(models.Messages.created_at.desc())
                .subquery()
            )
            query = self.db.session.query(models.Conversations, messages_subquery)
            query = query.filter(models.Conversations.user_email == user_email, models.Conversations.project_name == project_name)
            query = query.order_by(models.Conversations.updated_at.desc()).limit(500).offset(curr_count)

            result = query.all()    
            return result
        finally:
            self.db.session.close()

    # Document group-related queries

    def getDisabledDocGroups(self, course_name: str):
        try:
            query = self.db.select(models.DocGroup.name).where(models.DocGroup.course_name == course_name, models.DocGroup.enabled == False)
            result = self.db.session.execute(query).scalars().all()
            document_groups: List[models.DocGroup] = [doc_group for doc_group in result]
            return DatabaseResponse[models.DocGroup](data=document_groups, count=len(result))
        finally:
            self.db.session.close()

    # N8N Workflow-related queries

    def getLatestWorkflowId(self):
        try:
            query = self.db.select(models.N8nWorkflows.latest_workflow_id)
            result = self.db.session.execute(query).fetchone()
            return result
        finally:
            self.db.session.close()
    
    def lockWorkflow(self, id: int):
        try:
            new_workflow = models.N8nWorkflows(is_locked=True)
            self.db.session.add(new_workflow)
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    def deleteLatestWorkflowId(self, id: int):
        try:
            query = self.db.delete(models.N8nWorkflows).where(models.N8nWorkflows.latest_workflow_id == id)
            self.db.session.execute(query)
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    def unlockWorkflow(self, id: int):
        try:
            query = self.db.update(models.N8nWorkflows).where(models.N8nWorkflows.latest_workflow_id == id).values(is_locked=False)
            self.db.session.execute(query)
            self.db.session.commit()
        finally:
            self.db.session.close()
    
    def check_and_lock_flow(self, id):
        try:
            query = text("SELECT check_and_lock_flows_v2(:id)")
            result = self.db.session.execute(query, {"id": id}).fetchone()
            return result
        finally:
            self.db.session.close()
    

    # Pre-Authorized API Key-related queries

    def getPreAssignedAPIKeys(self, email: str):
        try:
            result = models.PreAuthAPIKeys.query.filter(models.PreAuthAPIKeys.emails.contains(f'["{email}"]')).all()
            return result
        finally:
            self.db.session.close()
    
    

    

