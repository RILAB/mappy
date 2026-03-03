1. Git repo check
- If the current directory is not a git repository, ask the user whether they want to create one before making changes.

2. Data-file permission (always ask)
- Always request permission before modifying any data file.
- User instructions such as “modify,” “remove,” “edit,” or similar do **not** count as permission for data files. You must still ask.

3. Data-file definition
- A data file is any non-code project file, especially plain-text files used as inputs, outputs, configuration, or reference data.
- Examples include: `*.txt`, `*.csv`, `*.tsv`, `*.fastq`, `*.fastq.gz`, `*.md`, `*.sam`, `*.maf`, `*.yaml`, `*.yml`, `*.json`, `*.map`, `*.bed`, `*.vcf`, `*.gvcf`, `*.fai`, and similar tabular or reference files.
- If unsure whether a file is a data file, treat it as a data file and ask permission first.

4. Uncommitted changes check (target file only)
- Before modifying a file, check whether the **target file** has uncommitted changes.
- If the target file has uncommitted changes, ask whether the user wants to commit those changes first.
- This rule is target-file-only (not repo-wide).

5. One permission can cover multiple files
- A single permission request is sufficient if the user clearly authorizes modifying multiple specific data files in the same task.

6. Backups for data files
- When modifying a data file (with permission), create a backup copy first using the `.bak` suffix (for example, `file.txt.bak`).

7. Symlink write policy
- If a path to be modified is a symbolic link, never modify the symlink target.
- If modification is required (with permission), create a regular-file copy in the current working directory, modify that copy, and replace the symlink path with the modified regular file.
- Prefer `path.tmp` + atomic rename (`mv path.tmp path`) so the symlink is replaced by a regular file.
- Do not use in-place editors (`sed -i`, `perl -pi`, etc.) on symlink paths.
- If a backup is required, back up the symlink path as it exists before replacement.
- If a symlink is replaced, create or append an entry in `symlinks.md` (in the repository root) recording: the original symlink path, the original symlink target path, and the replacement file path (the path after replacement).

8. Write scope restriction
- Do not create, modify, or delete files outside the current working directory unless the user explicitly requests it.
- Exception: temporary files may be created or modified in `/tmp` and system temporary directories (for example, macOS `/var/folders/...`) when needed for task execution.
- Files written to `/tmp` should be treated as temporary working files, not final outputs, unless the user explicitly requests otherwise.
- This rule does not permit modifying symlink targets outside the current working directory; symlink paths must follow the symlink write policy.
- Tool-generated temporary files, caches, and logs are allowed in the current working directory or approved temporary directories when required to complete the task.


9. Data-file permission exception (temporary paths)
- Permission is not required for creating or modifying data files under `/tmp` or system temporary directories (for example macOS `/var/folders/...`) when they are temporary working files used to run, test, or validate the project.
- This exception does not apply to files in the repository working directory (including `tests/`, `results/`, `example_data/`, `config.yaml`, `README.md`, `*.md`, etc.) or any other non-temporary location.
- Temporary files created under `/tmp` remain subject to the symlink write policy if the target path is a symlink.
- The agent should prefer `/tmp/<project>-<purpose>/...` paths for temporary data outputs to make scope explicit.

10. Bootstrap AGENTS.md into repos

If AGENTS.md is missing in the current git repository root, copy the default AGENTS.md into that repository before doing other work.
Do not overwrite an existing AGENTS.md.
If the current directory is not a git repository, follow the existing git-repo check rule first.
