from dataclasses import dataclass, field


@dataclass
class DerivedClaim:
    value: str
    sources: list[str]


@dataclass
class SourceArtifact:
    path: str
    sha256: str
    size_bytes: int


@dataclass
class ContextConflict:
    field: str
    claims: list[DerivedClaim]
    reason: str = "Source declarations differ; compatibility has not been verified."


@dataclass
class ProjectContext:
    project_name: DerivedClaim | None = None
    project_summary: DerivedClaim | None = None
    detected_technologies: list[DerivedClaim] = field(default_factory=list)
    entry_points: list[DerivedClaim] = field(default_factory=list)
    test_commands: list[DerivedClaim] = field(default_factory=list)
    important_files: list[DerivedClaim] = field(default_factory=list)
    architecture_notes: list[DerivedClaim] = field(default_factory=list)
    assumptions: list[DerivedClaim] = field(default_factory=list)
    sources: list[SourceArtifact] = field(default_factory=list)
    trust_level: str = field(default="Derived Context / Interpretation", init=False)
    python_requirements: list[DerivedClaim] = field(default_factory=list)
    conflicts: list[ContextConflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bytes_read: int = 0
