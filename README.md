# DifPrivSTLLearning

Folder Breakdown:
- Data: Raw data and the learned STL rules. 
  - The three main datasets are the ICU data, Sepsis and T1D. Synthetic is a test ruleset I made to evaluate the protocol.
  - If you want to see the actual rules, go to Dataset/Best/PatientNum for example to see the first patient's rules for ICU go to ICU/Best/1000Rules.txt. (Each number is a client identifier / Patient ID).
- MCTS: Monte Carlo Tree Search code
  - MCTS.py is a template search method (with no privacy)
  - MCTS_Baseline.py is the baseline search method with privacy where the budget per query is the same for all queries (Reference this one!). 
  - MCTS_Coverage.py is a failed expoloration of adapting the MCTS search (Don't use this one)
- MetricCalculation: Contains the experimental code- specifically the code to compute the Coverage and Rule Quality experiments
- Paper: Contains graphs and images used in the Qualifying Exam Report
- Param_Results: Experimental Results folder for the parameters
- QueryExploration: Leftover code from when I was playing around with different search methods (not relevant)
- Results: Old Experimental results from the baseline and coverage adapted methods
- RuleTemplate: Contains the code for the rule template data structure 
  - RuleTemplate.py is the object class that contains the rule tree we search
  - RuleTree.py allows for printing of the rule template tree (just allows for easier manipulation and analysis of the tree, but don't need to use)
- STLTree: STL Grammar object definitions
- SignalTemporalLogic: Allows grammar parsing and analysis. Includes a tokenizer, lexer, parser and method(s) to traverse the STL grammar

Important Files:
- Client.py is the code that contains the functions run by each individual (local) client
- Server.py is the central server that is sending queries to the clients and collects and aggregates the rule structures
- Main.py is the main runner pipineline (use this one to run the code, this runs the nonprivate version)
- Run_Experiments_Private.py runs a set of experiments with different privacy budgets using the baseline privacy version (MCTS_Baseline) <-- this is probably the main one to look at
- params.py is the script containing the parameters needed to run the protocol
