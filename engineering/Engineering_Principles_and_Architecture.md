# Engineering Principles & Architectural Rationale

**Project:** Submission & Approval Workflow
**Candidate:** Makai Kahilu
**Purpose:** The companion to the Engineering Playbook. Where that document specifies *what* to build, this one explains *why* it's built this way — the engineering reasoning behind every structural choice, so any decision in the codebase can be traced to a principle rather than a habit.

---

## 0. How to Read This Document

The Engineering Playbook is the build contract: file layout, code, commands, test matrices. This document is the reasoning underneath it. Every principle here is stated as a standard this codebase holds itself to, illustrated with code from *this* project — not borrowed examples.

A useful way to navigate the three concerns these principles span:

```text
Language-level     →  How Python itself behaves, and how to use it safely
                      (functions, exceptions, the object model, packages)

Framework-level    →  How to arrange Django/DRF so the code stays correct
                      and maintainable as it grows
                      (where logic lives, settings, queries, security)

Workflow-level     →  How to move through the build without losing work,
                      breaking things silently, or shipping something
                      you can't explain
                      (save points, view composition, test discipline)
```

A quick test for which layer a question belongs to: *"why does `super()` resolve to that method?"* is language-level. *"where should this validation live — model or view?"* is framework-level. *"what do I type next, and how do I know I haven't broken anything?"* is workflow-level.

---

## 1. The Architecture in One Picture

```text
React UI
  → API client (HTTP, response parsing)
    → DRF boundary (ViewSets: request in, response out)
      → Serializers + Permissions (validation, access gates)
        → Workflow service (the single home of every transition rule)
          → Models / QuerySets / PostgreSQL (durable state, fixed query budgets)
            → Tests prove every layer; README explains every decision
```

The non-negotiable property of this architecture: **business legality is decided in exactly one place** — the workflow service — and every other layer either feeds it inputs or renders its outputs. Nothing above the service decides whether a transition is allowed. This is what makes the system testable without a browser, auditable without guesswork, and secure regardless of what the UI happens to show.

---

## 2. Language-Level Principles

### 2.1 Functions Are Self-Contained and Side-Effect-Honest

A function should operate only on what's passed to it, return the same result for the same arguments, and avoid hidden side effects. Its name and argument list *are* its contract.

This is why the workflow transition functions are keyword-only and take everything they need explicitly, rather than reaching into `request` or global state:

```python
def reject_application(*, application: Application, actor, comment: str) -> Application:
    ...
```

No `request` object, no implicit `self.request.user` — data in, object out or exception raised. The function is unit-testable without DRF, without HTTP, without a browser. Two supporting rules follow directly:

- **Never use a mutable default argument.** `details: dict | None = None` is the correct idiom, because a default is created once at definition time, not per call — a `details: dict = {}` default would be silently shared across every call.
- **Force keywords for anything optional.** The leading `*` makes every call site self-documenting (`approve_application(application=app, actor=user)` reads correctly without consulting the signature).

### 2.2 Assertions Are Never Business or Security Validation

`assert` checks *program invariants* — internal "this should never happen" conditions — never user input or business rules. The reason is mechanical: assert statements are stripped entirely when Python runs under the `-O` optimization flag. Any rule enforced by `assert` silently stops being enforced in that mode.

So the workflow service never writes `assert actor.is_reviewer`. It raises `WorkflowPermissionDenied` instead — the function explicitly *decides* to fail, rather than hoping an interpreter flag is never set. This single discipline is what keeps every authorization and transition rule real in all runtime configurations.

### 2.3 Exceptions: Catch Narrow, Let the Rest Propagate, Never Swallow

The exception strategy has three rules: handle only the specific exceptions you have a real recovery story for, let everything else propagate, and never catch a broad `Exception` without re-raising or logging — that hides the actual failure and turns a bug into a mystery for whoever debugs it next.

This is the entire justification for an application-specific exception hierarchy:

```python
class WorkflowError(Exception):              # app-specific base, not bare Exception
    code = "workflow_error"
    status_code = 400

class InvalidTransition(WorkflowError):       # narrow, named, recoverable at the boundary
    code = "invalid_transition"

class WorkflowPermissionDenied(WorkflowError):
    code = "permission_denied"
    status_code = 403
```

The view layer catches `WorkflowError` *specifically* — never `Exception` — and translates it into a structured response. Anything outside that hierarchy (a real bug, a database error) propagates and surfaces as a 500, exactly as it should. A silent `except Exception: pass` around a transition would be the single most dangerous line in this codebase: it would make a failed audit-log write look like a successful approval.

### 2.4 Atomic State Changes via Context Managers

A `with` block is the correct tool whenever something must be cleaned up reliably or executed all-or-nothing. `transaction.atomic()` is precisely this pattern at the database layer: it guarantees the status change and the audit-log write either both land or neither does. There is no path through `_transition()` where status changes but the audit row doesn't — the `with transaction.atomic():` block makes them one indivisible unit, not two statements that could be interrupted between them.

### 2.5 Classes: Properties and Composition, Used Deliberately — Not by Default

- **Properties add computed behavior without changing the public interface.** `Application.is_editable_by_applicant` and `Application.is_reviewable` are properties, not stored fields — so derived logic can change later without breaking any caller already using `application.is_reviewable`.
- **Memory micro-optimizations (`__slots__`) are for purpose-built data containers, used sparingly — never reflexively.** Django models are explicitly *not* candidates (the ORM needs the full instance dictionary); reaching for an optimization just because it exists is the failure mode to avoid.
- **The single-underscore convention marks implementation, not enforcement.** `_locked_application`, `_require_owner`, `_require_reviewer`, `_require_status`, `_require_comment` are module-internal helpers — the underscore signals "not part of the public contract," cleanly separating the five public transition functions from the machinery behind them.

### 2.6 Why Mixin Composition Actually Works (and the Rule It Implies)

Python's method resolution order (MRO) — computed by C3 linearization across multiple base classes — has three practical consequences worth internalizing:

1. `super()` does not call "the parent class." It calls *the next class in the MRO*, which depends on the entire inheritance chain, not just the immediate base.
2. Cooperative multiple inheritance only works if every class in the chain calls `super()`. A class that calls a specific parent directly instead breaks the chain for anything composed with it.
3. Order matters — base-class ordering changes the resulting class.

This is the actual mechanism behind composable access-control classes and DRF's generic-view machinery: a behavior mixed in *to the left* of a concrete class takes effect because its method calls `super()`, which the MRO resolves forward to the concrete implementation. The rule this implies for our own code: **any mixin or permission class we write calls `super()`, never skips it, and never assumes it sits directly above a specific parent.** That's what keeps our own composable pieces actually composable.

### 2.7 What's Underneath the "Magic"

Two language features explain framework behavior that otherwise looks like sorcery, and knowing they exist stops them from being mysteries:

- **Descriptors.** Attribute access on a class isn't plain dictionary lookup — Python checks for `__get__`/`__set__` on the class attribute first. This is what lets a model field declared as a class attribute run validation, type coercion, and (for relations) a query underneath, while still reading like a plain attribute on instances. `application.status = "SUBMITTED"` and `serializer.validated_data["comment"]` are both descriptor-mediated, which is *why* you can't just monkeypatch around them.
- **Metaclasses.** The ORM's model machinery and DRF's serializer machinery are metaclasses — classes that build classes. That's how declaring `class Application(models.Model): title = models.CharField(...)` yields a fully wired class with a manager, a `Meta`, and field descriptors without you writing that plumbing. We never write our own metaclass here, but recognizing this is what makes "why does subclassing give me all this for free" a known quantity rather than a black box.

### 2.8 Package Hygiene

Two rules govern `applications/services/`:

- **One-directional dependencies; no import cycles.** `workflow.py` imports from `models.py` and `exceptions.py`, never the reverse. A directed, acyclic import graph is the practical antidote to circular-import bugs.
- **A deliberate public surface via `__init__.py`.** `applications/services/__init__.py` re-exports exactly the five public transition functions and nothing else. Callers write `from applications.services import approve_application`, never `from applications.services.workflow import _require_reviewer`. Every `_private` helper stays behind the package boundary.

---

## 3. Framework-Level Principles

### 3.1 Keep It Simple

Every piece of unnecessary complexity makes the system harder to extend and maintain, so the target is always the simplest solution that doesn't make a bad assumption. This is the direct justification for the scope discipline in the Engineering Playbook — no background-job queue, no generic pluggable workflow engine, no file-attachment handling. None of it is asked for, and each would dilute the workflow-and-authorization correctness that the assessment actually weights heavily.

### 3.2 Where Code Lives: Fat Models, Service Modules, Thin Views, Passive Templates

This is the core placement framework, and it's a four-way split — not the abbreviated "fat models, thin views":

| Layer | Role | In this project |
|---|---|---|
| **Fat models** | Logic intrinsically about *the data* — methods, properties, simple invariants | `Application.is_editable_by_applicant`, `Application.is_reviewable`, the `ApplicationQuerySet` selectors |
| **Service modules** | Reusable logic that belongs to no single model — its own module, separate from models *and* views | `applications/services/workflow.py` + `exceptions.py`: the workflow spans the application, the actor, and the audit log together, so it's neither a model method nor view logic |
| **Thin views** | Translate HTTP ↔ domain calls; never decide business legality | Each DRF action is ~4 lines: get object, call service, catch `WorkflowError`, respond |
| **Passive templates** | Display only; never compute. (Here the "template" is the React frontend — same rule) | React renders `status`, `audit_logs`, and validation errors the API hands over; it never independently decides whether a transition is legal |

The service module is genuinely a third category, not a subset of "fat models." Putting the workflow in its own module — rather than scattering `Application.submit()`, `Application.approve()` instance methods across the model — is the deliberate application of that distinction.

### 3.3 Start With the Framework's Defaults

Before reaching for a different ORM, a different database, or a custom API layer, build with the framework's own defaults and only replace a core component once a real, specific obstacle justifies it. This project follows that directly: PostgreSQL, the built-in ORM, DRF's standard `ModelViewSet` / `ReadOnlyModelViewSet`, and the framework's own session and permission systems. Nothing here has hit a wall that would justify swapping a core piece out — so nothing is swapped.

### 3.4 Imports: Relative Within an App, Absolute Across App Boundaries

A precise rule that's easy to get half-right:

- **Within a single app**, internal imports are relative (`from .models import Application`). An app is meant to be a relocatable package; hardcoding the project's top-level name into every internal import ties it to one layout for no benefit.
- **Across app or package boundaries** (e.g. `users` importing from `applications`, or importing project settings), imports are absolute, because that's where naming ambiguity is the real risk.

These aren't in tension — they're the same rule at two zoom levels. Inside `applications/`, imports between the app's own modules are relative; anything reaching across to another app is absolute. This project applies that consistently, regardless of how any given scaffold file happens to do it.

### 3.5 Configuration Lives in the Environment

Configuration belongs in environment variables, not in code, and a deployable artifact should be identical across environments with only its environment variables changing. This is why `.env.example` exists, why `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` are environment-driven in production settings, and why local/test/production settings are split modules rather than one file with `if DEBUG:` branches scattered through it.

### 3.6 Model Field Precision, and No Files in the Database

- `null=True` is a database concern (can the column store `NULL`); `blank=True` is a validation concern (can the field be submitted empty). They're independent, set deliberately per field — never copy-pasted as a reflexive pair.
- Binary file content never goes in the database directly — it bloats backups and forces every read through both the app and DB layers. The decision to defer file attachments sidesteps this entirely; if attachments are added later, they're a `FileField` pointing at storage, never bytes in a column.

### 3.7 Queries: Chainable, Lazy, and Budgeted

Two query habits, both visible in `ApplicationQuerySet`: build readable, chainable querysets (`for_applicant`, `for_reviewer_queue`, `submitted_or_under_review`, `with_owner`, `with_audit_trail`) rather than repeating a large filter expression at every call site, and rely on the ORM's lazy evaluation rather than dropping to raw SQL until there's a demonstrated reason. Nothing in this project needs raw SQL.

This is also where a real performance contract lives. Every read path has a **fixed query budget that doesn't grow with row count**:

- List endpoints fold the owner lookup into a single JOIN (`select_related`) and *never* nest the audit trail — nesting a one-to-many in a list response is exactly what turns one query into 1 + N.
- Detail and transition responses prefetch the audit trail *and its actors* (`prefetch_related` with a nested `select_related`), so a fifty-entry trail is a constant handful of queries, not fifty-one.

The discipline: if a serializer field renders a new relation, the queryset helper is extended to load it — the serializer is never allowed to trigger the query lazily, one row at a time.

### 3.8 One Serializer Per Use Case

Purpose-built serializers beat one serializer juggling every state of an object's lifecycle. The split — `ApplicationCreateSerializer`, `ApplicationUpdateSerializer`, `ApplicationListSerializer`, `ApplicationDetailSerializer`, `TransitionCommentSerializer` — gives each one a single job with its own read-only fields, rather than one serializer full of conditional logic for "is this a create, an update, a list row, or a detail view." The list-vs-detail split is also a performance boundary (§3.7): the list serializer deliberately omits the audit trail.

### 3.9 Security Defaults Are Not Optional; Signals Are a Last Resort

Two rules easy to skip under deadline pressure:

- Production runs with `DEBUG=False` and secrets from the environment, never committed.
- Signals are a last resort for cross-cutting behavior, not a default tool, because they make the causal chain — "what code actually ran, and when?" — hard to trace by reading the code that triggered it.

The second is the direct reason audit-log creation happens *explicitly* inside the workflow service, in the same function and transaction as the status change — never via a `post_save` signal that would fire from anywhere a save happens, including places you never intended. The audit trail is only trustworthy if its creation is in the one code path that's supposed to create it.

### 3.10 Documentation Is a Deliverable

Documentation is treated as first-class, not an afterthought — which is why the README covers not just "how to run it" but the data model, the workflow rules, the API contract, the testing strategy, and the trade-offs. A reviewer should never have to read the source to answer "why does this exist."

---

## 4. Workflow-Level Principles

Framework principles say where code belongs. These say how to actually move through the build without losing work, breaking things silently, or shipping something you can't explain.

### 4.1 Read the Scaffold Before You Fight It

The generated project scaffold is a tool, not an obstacle: generate it, then *read* what it produced (the settings split, the Docker compose files, the seeded users app) before changing anything. That's the deliberately-sequenced "Foundation" phase in the Engineering Playbook, placed before any domain code. The exact commands and setup gotchas live there (§9.1); this principle is just *why* understanding the scaffold comes before modifying it — and why we apply our own consistent conventions on top of it rather than mirroring whatever any individual scaffold file happens to do.

### 4.2 Why Class-Based / Generic Views Win Here

Generic, class-based views earn their place for three concrete reasons, all of which this project uses:

1. **Composition** — a mixin defines behavior once; every view inheriting it gets that behavior without copy-paste. `IsApplicant` / `IsReviewer` as DRF permission classes are this idea applied to access control.
2. **Intelligent defaults** — a generic ViewSet infers serializer, response shape, and queryset from a few attributes, so the common case isn't hand-written dispatch.
3. **Standardized method handling** — undefined HTTP methods get the framework's default (405) instead of every view re-implementing method checks.

The discipline that comes with them: stick to the defaults, don't go multiple-inheritance-crazy, and drop to a plain base view only when something genuinely doesn't fit. Our ViewSets follow exactly this — a single permission class, `get_serializer_class()` / `get_queryset()` overridden only where the default genuinely doesn't apply, and explicit `@action` methods for the four transitions rather than smuggling transition logic into a generic `update()`.

### 4.3 Authorization Declared on the Class

Requiring a role should be one line in the class declaration, not a check duplicated through every method. `permission_classes = [IsApplicant]` as a class attribute is authorization you can audit by reading the class definition once — not by tracing logic scattered across method bodies. (And it's the *first* of two independent gates; the workflow service's own `_require_owner` / `_require_reviewer` is the second, so a bug in one layer doesn't expose the system.)

### 4.4 Test the Real Behavior, Including the Boring Cases

- **Every model method gets a test — including the trivial-looking ones.** A `__str__` or a property looks too small to test, but nothing guarantees its behavior won't silently change later, and catching that in a test is cheaper than catching it in front of a user. Model tests are a named category in the Definition of Done, not an afterthought.
- **Coverage is a ratchet, not a vanity number.** The rule worth keeping literally: every time you add code, check coverage — if it drops, you're losing; if it holds, you've drawn; if it rises, you're winning. `coverage run -m pytest && coverage report` is a check run *before* commits, not just before submission.

### 4.5 Factories Reduce Effort and Risk

Building test objects with explicit `Model.objects.create(...)` at every call site isn't just more typing — it forces you to know the exact field set everywhere, and any value you didn't bother to vary tends to encode an accidental assumption that can mask bugs. `ApplicantFactory`, `ReviewerFactory`, and `ApplicationFactory` solve both. The complementary rule: still pass explicit field values *when the test is about that field* (`application_factory(status=Application.Status.DRAFT)`), not in the general case.

### 4.6 The Admin Is Power, Not the Product

Admin access is disproportionate power relative to what most users should have, so it stays small and is never the primary way anyone — including you — interacts with day-to-day data. This is the specific, recurring reason behind the "admin is for inspection only, never the product UI" rule throughout the Engineering Playbook. The admin exists to *look at* applications and audit rows, not to drive the workflow.

### 4.7 Commit at Every Working Slice

You're going to change many files and it's easy to break things and lose work; the fix is committing at each point where the code is in a known-good state — not occasionally, not "end of day." The Engineering Playbook's commit plan makes this literal: each commit is one verified, working slice (models → admin → factories → workflow service → workflow tests → serializers → permissions → …), so a broken intermediate state is never the only copy of your work.

### 4.8 Vet a Dependency Before Adopting It

Before adding any dependency: check for alternatives, check the project's repository activity as a maintenance signal, check the most recent release date, then install. This is the due diligence behind every package in the stack, and it's worth re-running before adding anything new rather than reaching for the first package that appears to solve the problem.

---

## 5. Principle → Where It Lives

| Principle | Lives in |
|---|---|
| Keyword-only, side-effect-free functions | `workflow.py` transition functions |
| Never `assert` for business/security rules | `_require_*` helpers raise exceptions |
| Narrow exception catching, app-specific hierarchy | `WorkflowError` hierarchy + view-layer `except WorkflowError` |
| Context managers for atomic operations | `transaction.atomic()` around every transition |
| Properties for computed, interface-stable attributes | `is_editable_by_applicant`, `is_reviewable` |
| Micro-optimizations used sparingly, not by default | `__slots__` correctly *not* applied to models |
| `super()` discipline behind composable classes | `IsApplicant` / `IsReviewer` and any future mixin |
| Relative imports within an app, absolute across | App-internal imports relative; cross-app absolute |
| Keep it simple — no speculative features | No queue, no file handling, no generic workflow engine |
| Fat models / service modules / thin views | Model properties + `services/workflow.py` + 4-line actions |
| Start with framework defaults | Stock Postgres, ORM, DRF generics |
| Config in the environment | `.env.example`, split settings modules |
| `null` vs `blank` precision; no files in DB | Field definitions; attachments deferred |
| Chainable, lazy, budgeted queries | `ApplicationQuerySet` + the fixed query budget |
| One serializer per use case | Create / Update / List / Detail / TransitionComment |
| Signals as last resort | Audit logging explicit in `workflow.py`, never `post_save` |
| Documentation as a deliverable | README + this document |
| Read the scaffold before changing it | Foundation phase of the build order |
| Generic-view composition / defaults / dispatch | `ModelViewSet` / `ReadOnlyModelViewSet` usage |
| Authorization declared on the class | `permission_classes = [...]` |
| Test every method, including the boring ones | Model + workflow test matrix |
| Coverage as a ratchet | Pre-commit quality gate |
| Factories over manual object creation | `ApplicantFactory` / `ReviewerFactory` / `ApplicationFactory` |
| Admin is power, not the product | Admin = inspection only |
| Commit at every working slice | The commit plan |
| Vet dependencies before adopting | Stack / dependency choices |

---

## 6. One Feature, Every Principle, End to End

The hardest transition in the system — **reject, with a required comment** — traced through every principle that shapes it. Each annotation names the principle, not a source.

```python
# applications/services/exceptions.py
class CommentRequired(WorkflowError):          # app-specific exception, not a built-in,
    code = "comment_required"                  # not a bool/None return on failure


# applications/services/workflow.py
def reject_application(*, application: Application, actor, comment: str) -> Application:
    # keyword-only args -> self-documenting call site
    with transaction.atomic():
        # context manager guarantees status + audit log change together or not at all
        application = _locked_application(application)
        # row-locked read via a queryset method, not raw SQL

        _require_reviewer(actor=actor)
        # authorization as an explicit gate -- raises, never asserts

        _require_status(
            application=application,
            allowed={Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW},
            message="Only submitted or under-review applications can be rejected.",
        )
        # the business rule lives in the service module: it spans actor + object + audit log

        comment = _require_comment(comment=comment)
        # required comment enforced by an explicit exception -- holds even under python -O

        return _transition(application=application, actor=actor,
                            to_status=Application.Status.REJECTED,
                            comment=comment, reviewed=True)
        # audit log written explicitly inside this function, same transaction --
        # never via a post_save signal


# applications/views.py
class ReviewerApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsReviewer]
    # declarative authorization as a class attribute -- the first of two gates

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        # thin action: validate input, call service, catch the one exception
        # type that matters, respond
        serializer = TransitionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # one serializer, one job: "is there a non-blank comment" -- nothing about legality

        application = self.get_object()
        try:
            application = reject_application(application=application, actor=request.user,
                                               comment=serializer.validated_data["comment"])
        except WorkflowError as exc:
            # catch the narrow, named type -- never `except Exception`; the rest is a 500
            return workflow_error_response(exc)
        return self._transition_response(application)
        # re-reads through the fixed-budget detail queryset so the response carries
        # the new audit row without a per-row lazy load
```

```python
# applications/tests/test_workflow.py
@pytest.mark.django_db
def test_reject_without_comment_raises(application_factory, reviewer):
    # factory instead of manual Application.objects.create(...)
    application = application_factory(status=Application.Status.SUBMITTED)

    with pytest.raises(CommentRequired):
        reject_application(application=application, actor=reviewer, comment="   ")

    application.refresh_from_db()
    assert application.status == Application.Status.SUBMITTED
    assert application.audit_logs.count() == 0
    # test the boring negative case too: a no-op transition leaves zero audit rows
```

Roughly a dozen distinct principles in about thirty lines of one real feature, none decorative. Remove any one — drop the `transaction.atomic()`, swap the exception for an `assert`, catch `Exception` instead of `WorkflowError`, write the audit log in a signal, nest the trail in a list response — and the feature still *demos* fine, but loses the specific guarantee that principle was protecting.

---

## 7. Where Principles Compete (and the Call Made Here)

No principle set is free of tension. The genuine ones, and how this project resolves them:

**Relative vs. absolute imports.** Resolved in §3.4 — relative within an app, absolute across boundaries. Restated here because it's the most likely "wait, didn't the other rule say the opposite?" moment.

**`unittest` vs. `pytest`.** The standard-library test framework is worth knowing exists, but this project commits fully to `pytest` + `pytest-django` + `factory_boy`. There's nothing the class-based style buys that plain `assert`-based functions and fixtures don't cover more concisely, and the assessment's own framing implies pytest-style testing.

**Function-based vs. class-based vs. generic views.** Both function- and class-based views are legitimate, and the honest guidance is "generic/CBV for standard CRUD-shaped views, FBV when the logic genuinely doesn't fit a generic pattern." This project's endpoints are uniformly CRUD-plus-a-few-named-actions — exactly the shape generic ViewSets handle best — so there's no real disagreement to resolve here, even though the general principle leaves room for one.

**The scaffold is not a style guide.** The generated project template is a strong, production-shaped foundation, but its individual files aren't perfectly self-consistent (the seeded users app, for instance, mixes relative and absolute imports for same-app modules). The resolution: follow the *principle* (the layering and import conventions above) as the durable thing, and treat the scaffold's literal file-by-file choices as one implementation to build on, not a canonical pattern to copy. This project's own `services/` layer is exactly that kind of intentional addition on top of the foundation — the bare scaffold doesn't generate a service layer; we add one because the placement principle in §3.2 calls for it.

---

## 8. Pre-Commit Principle Checklist

Run this against any new code before committing:

```text
[ ] Does this avoid `assert` for anything that must always hold?
[ ] Does every raised error use a named, application-specific exception?
[ ] Is any multi-step state change wrapped in transaction.atomic()?
[ ] Could this be tested without spinning up HTTP/DRF? If not, why not?
[ ] Does this belong on the model, in services/, or genuinely in the view --
    and have I checked it isn't quietly becoming an undocumented fourth category?
[ ] Is authorization declared on the class, not buried in a method body?
[ ] Does any read path I touched still have a fixed query budget --
    no audit trail nested in a list, no relation lazy-loaded per row?
[ ] Did I add a test, including for "just" a property or __str__?
    Did coverage hold or rise?
[ ] Did I use a factory instead of spelling out every field?
[ ] Is this import relative (same app) or absolute (different app) -- correctly?
[ ] Am I about to add a signal? Could it instead be an explicit call in the
    one place that needs it?
[ ] Am I about to add a dependency? Have I checked it's maintained?
[ ] Is this the simplest version that doesn't make a bad assumption --
    or have I started building a framework nobody asked for?
```

Every box honestly checked means the code isn't just working — it's working for reasons that hold up under review.
