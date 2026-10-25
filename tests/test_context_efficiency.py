import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.knowledge_rag import KnowledgeRetriever
from core.tools import ToolExecutor


class ContextEfficiencyTests(unittest.TestCase):
    def test_budget_and_deduplication(self):
        retriever = KnowledgeRetriever()
        row = dict(path='test.md', line=1, end_line=3, heading='Test', excerpt='evidence ' * 100)
        with patch.object(retriever, 'search', return_value=[row, row]):
            for budget in (0, 1, 20, 100, 3500):
                context = retriever.get_context_for_prompt('query', max_chars=budget)
                self.assertLessEqual(len(context), budget)
            self.assertEqual(retriever.get_context_for_prompt('query').count('###'), 1)

    def test_file_paging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sample.txt').write_text('\n'.join(str(i) for i in range(500)))
            executor = ToolExecutor(root)
            first = executor.execute_tool('read_file', {'path': str(root / 'sample.txt')})
            self.assertEqual(first['end_line'], 120)
            self.assertEqual(first['next_start_line'], 121)
            self.assertEqual(first['total_lines'], 500)
            last = executor.execute_tool('read_file', {'path': str(root / 'sample.txt'), 'start_line': 421})
            self.assertFalse(last['truncated'])
            self.assertIsNone(last['next_start_line'])

if __name__ == '__main__':
    unittest.main()
