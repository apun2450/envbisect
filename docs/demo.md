# Record the 46-difference demo

The demo uses synthetic data and a deterministic program. It shows 46 changed variables and ends with `FEATURE_CACHE` and `TZ`. Neither change makes the demo fail alone.

Install EnvBisect from the repository root once:

```bash
python -m pip install -e .
```

Run the recording script from the repository root. Each script also works when invoked by an absolute path from another directory:

```bash
sh scripts/demo.sh
```

On PowerShell:

```powershell
.\scripts\demo.ps1
```

Each script pauses briefly before the command and holds the final result for 12 seconds. On a typical machine, a recording takes about 15–25 seconds; the direct README command has no pauses. The command itself must exit successfully and show `46 environment differences found.` followed by `FEATURE_CACHE` and `TZ`.

To create a local GIF with the open-source [asciinema recorder](https://docs.asciinema.org/manual/cli/quick-start/) and [agg renderer](https://docs.asciinema.org/manual/agg/usage/) on macOS, Linux, or WSL:

```bash
asciinema rec -c "sh scripts/demo.sh" demo.cast
agg --idle-time-limit 20 --cols 100 --rows 28 --last-frame-duration 3 demo.cast demo.gif
```

Use a terminal around 100 columns by 28 rows. Inspect the GIF for the `46` count and both final variable names. The repository ignores generated casts and GIFs so a recording is reviewed before it is shared or added deliberately. If using PowerShell without WSL, an open-source screen recorder such as [OBS Studio](https://obsproject.com/) can capture `demo.ps1` directly.

Keep `--verbose` off for published recordings. Always inspect captured output before sharing; your own commands and environment snapshots may contain secrets.
