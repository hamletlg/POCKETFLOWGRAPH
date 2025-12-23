import os
import shutil
import logging

logger = logging.getLogger(__name__)

class WorkspaceManager:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.workspaces_dir = os.path.join(root_dir, "workspaces")
        self.default_workspace = "default"
        self.current_workspace = self.default_workspace
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensures the base workspaces directory exists."""
        os.makedirs(self.workspaces_dir, exist_ok=True)
        # Ensure default workspace exists
        self.create_workspace(self.default_workspace)

    def get_workspace_dir(self, workspace_name: str) -> str:
        return os.path.join(self.workspaces_dir, workspace_name)

    def get_workflows_dir(self, workspace_name: str) -> str:
        return os.path.join(self.get_workspace_dir(workspace_name), "workflows")
    
    def get_data_dir(self, workspace_name: str) -> str:
        return os.path.join(self.get_workspace_dir(workspace_name), "data")

    def create_workspace(self, name: str):
        path = self.get_workspace_dir(name)
        if not os.path.exists(path):
            os.makedirs(path)
            os.makedirs(os.path.join(path, "workflows"))
            os.makedirs(os.path.join(path, "data"))
            logger.info(f"Created workspace: {name}")
        return path

    def list_workspaces(self):
        if not os.path.exists(self.workspaces_dir):
            return []
        return [d for d in os.listdir(self.workspaces_dir) 
                if os.path.isdir(os.path.join(self.workspaces_dir, d))]

    def set_current_workspace(self, name: str):
        if not os.path.exists(self.get_workspace_dir(name)):
            raise ValueError(f"Workspace {name} does not exist")
        self.current_workspace = name
        logger.info(f"Switched to workspace: {name}")

    def get_current_workspace(self):
        return self.current_workspace

    def migrate_legacy_workflows(self, legacy_workflows_dir: str):
        """Moves files from old backend/workflows to backend/workspaces/default/workflows"""
        if not os.path.exists(legacy_workflows_dir):
            return

        target_dir = self.get_workflows_dir(self.default_workspace)
        
        # Check if legacy dir has JSON files
        files = [f for f in os.listdir(legacy_workflows_dir) if f.endswith(".json")]
        if not files:
            return

        logger.info(f"Migrating {len(files)} legacy workflows to {self.default_workspace}")
        for f in files:
            src = os.path.join(legacy_workflows_dir, f)
            dst = os.path.join(target_dir, f)
            if not os.path.exists(dst):
                shutil.move(src, dst)
            else:
                logger.warning(f"File {f} already exists in target, skipping migration.")

    def delete_workspace(self, name: str):
        if name == self.default_workspace:
            raise ValueError("Cannot delete default workspace")
        
        if name == self.current_workspace:
             raise ValueError("Cannot delete active workspace")

        path = self.get_workspace_dir(name)
        if not os.path.exists(path):
            raise ValueError(f"Workspace {name} does not exist")
        
        shutil.rmtree(path)
        logger.info(f"Deleted workspace: {name}")
