# AI Use Declaration Form

To be completed by the student. The fields follow the appendix to the AI Fundamentals syllabus.

| Field | Content |
|---|---|
| Assignment | Final Project, AI Fundamentals (AIF1303), group ______, Mustafa Kassym |
| AI Tool | _Tool or model name, version or date of use, access mode._ |
| Purpose of Use | _For example: idea generation, explaining a term, code checking, text editing, data analysis._ |
| Key Prompts | _Briefly list the main prompts or attach the prompt log._ |
| AI Contribution | _What exactly was created or modified with AI assistance._ |
| Result Verification | _How accuracy, sources, code, data, errors and risks were verified._ |
| Student Statement | I confirm that I am responsible for the final work and have accurately disclosed AI use. |

Signature: ____________________   Date: ____________________

## Facts that may help when filling in "Result Verification"

These are checks that exist in the repository and can be re-run by anyone:

- `python -m unittest discover -s tests` runs 90 tests: textbook values from Russell and Norvig (umbrella world), hand calculations, brute-force enumeration for Viterbi and for routes, closed-form MDP values, and requests against a live server.
- `python -m bagdar demo` prints the input, the key steps and the output of each algorithm so that every number can be recomputed by hand.
- `python -m bagdar experiments` reproduces the simulation tables from a fixed seed.
- `python -m bagdar realdata` re-fits the knowledge model on the public ASSISTments data and re-scores it on held-out students.
- Every numeric answer in the question bank was recomputed with a short script before it was accepted.
- Sources cited in the report are listed with DOI or URL; sources confirmed only through a secondary reference are marked as such.
