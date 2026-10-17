# Qwen3.6 thinking-on exploratory arm

This exploratory run used Qwen3.6 with thinking enabled and a 2,048-token generation cap. It was scored with the old strict JSON parser. Raw responses were not retained, so invalid-JSON cases cannot be rescored. Completed valid-JSON answers were correct on 43/49 questions (87.8%); the full run was budget-bound and is not a long-context quality result.
