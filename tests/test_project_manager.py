import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.project_manager as pm


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class ProjectGitStateChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "clones" / "demo-repo"
        self.repo.mkdir(parents=True)
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.email", "t@example.com")
        _git(self.repo, "config", "user.name", "t")
        (self.repo / "Dockerfile").write_text("FROM scratch\n")
        _git(self.repo, "add", "Dockerfile")
        _git(self.repo, "commit", "-q", "-m", "initial commit")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_registry_init_runs_no_git(self):
        with patch.object(pm, "_git") as git:
            manager = pm.ProjectManager(root=self.tmp)
        git.assert_not_called()
        self.assertIn("demo-repo", manager._projects)

    def test_state_matches_git_and_is_cached(self):
        manager = pm.ProjectManager(root=self.tmp)
        proj = manager.get_project("demo-repo")
        proj.refresh_git_info()
        self.assertEqual(proj.git_branch, "main")
        self.assertFalse(proj.git_dirty)
        self.assertTrue(proj.latest_commit.endswith("initial commit"))
        self.assertEqual(proj.key_files, ["Dockerfile"])

        (self.repo / "untracked.txt").write_text("x")
        with patch.object(pm, "_git") as git:
            proj.refresh_git_info()  # within TTL: served from cache
        git.assert_not_called()

        proj.refresh_git_info(force=True)
        self.assertTrue(proj.git_dirty)

    def test_list_projects_reports_state(self):
        manager = pm.ProjectManager(root=self.tmp)
        row = next(r for r in manager.list_projects() if r["id"] == "demo-repo")
        self.assertEqual(row["branch"], "main")
        self.assertFalse(row["dirty"])
        self.assertEqual(row["key_files"], ["Dockerfile"])


if __name__ == "__main__":
    unittest.main()
