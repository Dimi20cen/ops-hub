const entityListElement = document.getElementById("entity-list");
const resultMetaElement = document.getElementById("result-meta");
const resultPayloadElement = document.getElementById("result-payload");
const dryRunToggleElement = document.getElementById("dry-run-toggle");
const selectorTabProjectsElement = document.getElementById("selector-tab-projects");
const selectorTabHostsElement = document.getElementById("selector-tab-hosts");
const detailEmptyStateElement = document.getElementById("detail-empty-state");
const projectDetailPanelElement = document.getElementById("project-detail-panel");
const hostDetailPanelElement = document.getElementById("host-detail-panel");
const detailTabProjectViewElement = document.getElementById("detail-tab-project-view");
const detailTabProjectJsonElement = document.getElementById("detail-tab-project-json");
const detailTabHostViewElement = document.getElementById("detail-tab-host-view");
const detailTabHostJsonElement = document.getElementById("detail-tab-host-json");
const projectDetailViewElement = document.getElementById("project-detail-view");
const projectJsonViewElement = document.getElementById("project-json-view");
const projectJsonEditorElement = document.getElementById("project-json-editor");
const hostDetailViewElement = document.getElementById("host-detail-view");
const hostJsonViewElement = document.getElementById("host-json-view");
const hostJsonEditorElement = document.getElementById("host-json-editor");
const selectedProjectSlugElement = document.getElementById("selected-project-slug");
const selectedProjectTitleElement = document.getElementById("selected-project-title");
const selectedProjectSummaryElement = document.getElementById("selected-project-summary");
const selectedProjectSummaryReasonElement = document.getElementById("selected-project-summary-reason");
const selectedProjectDescriptionElement = document.getElementById("selected-project-description");
const selectedProjectHostElement = document.getElementById("selected-project-host");
const selectedProjectRuntimePathElement = document.getElementById("selected-project-runtime-path");
const selectedProjectPublicHealthElement = document.getElementById("selected-project-public-health");
const selectedProjectPrivateHealthElement = document.getElementById("selected-project-private-health");
const selectedHostSlugElement = document.getElementById("selected-host-slug");
const selectedHostTitleElement = document.getElementById("selected-host-title");
const selectedHostTransportElement = document.getElementById("selected-host-transport");
const selectedHostLocationElement = document.getElementById("selected-host-location");
const selectedHostRunnerHealthElement = document.getElementById("selected-host-runner-health");
const selectedHostRunnerUrlElement = document.getElementById("selected-host-runner-url");
const selectedHostSocketPathElement = document.getElementById("selected-host-socket-path");
const selectedHostTokenEnvVarElement = document.getElementById("selected-host-token-env-var");
const selectedHostNotesElement = document.getElementById("selected-host-notes");
const healthCheckButtonElement = document.getElementById("health-check-button");
const projectActionsElement = document.getElementById("project-actions");
const projectJsonSaveButtonElement = document.getElementById("project-json-save-button");
const projectJsonResetButtonElement = document.getElementById("project-json-reset-button");
const projectDeleteButtonElement = document.getElementById("project-delete-button");
const hostJsonSaveButtonElement = document.getElementById("host-json-save-button");
const hostJsonResetButtonElement = document.getElementById("host-json-reset-button");
const hostDeleteButtonElement = document.getElementById("host-delete-button");

const supportedActionNames = ["deploy", "start", "restart", "stop", "logs"];

let currentProjects = [];
let currentHosts = [];
let selectedEntityType = "projects";
let selectedProjectSlug = "";
let selectedHostSlug = "";
let selectedDetailView = "details";

function renderJson(value) {
    return JSON.stringify(value, null, 2);
}

function setResultPanel(titleText, payload) {
    resultMetaElement.textContent = titleText;
    resultPayloadElement.textContent = renderJson(payload);
}

function updateDryRunLabel() {
    dryRunToggleElement.setAttribute("aria-checked", String(dryRunToggleElement.checked));
}

function getStatusClassName(summaryValue) {
    if (summaryValue === "healthy") {
        return "healthy";
    }
    if (summaryValue === "partial") {
        return "partial";
    }
    if (summaryValue === "down") {
        return "down";
    }
    return "muted";
}

function applyStatusBadge(element, value) {
    const statusClassName = getStatusClassName(value);
    element.textContent = value;
    element.className = `status-badge status-badge-${statusClassName}`;
}

function getHealthCheckState(projectRecord, checkName) {
    return projectRecord.last_health_result?.checks?.[checkName] || null;
}

function describeHealthCheckState(checkName, healthCheckState) {
    const humanCheckName = checkName === "public" ? "Public" : "Private";
    if (!healthCheckState) {
        return `${humanCheckName} check has not run yet.`;
    }
    if (healthCheckState.status === "healthy") {
        return `${humanCheckName} check is healthy.`;
    }
    if (healthCheckState.status === "unconfigured") {
        return `${humanCheckName} check is not configured.`;
    }
    if (healthCheckState.status === "down") {
        const detailText = healthCheckState.detail || "The check failed.";
        return `${humanCheckName} check is failing: ${detailText}`;
    }
    return `${humanCheckName} check is ${healthCheckState.status}.`;
}

function buildProjectHealthReason(projectRecord) {
    const summaryValue = projectRecord.last_health_summary || "unknown";
    const publicCheckState = getHealthCheckState(projectRecord, "public");
    const privateCheckState = getHealthCheckState(projectRecord, "private");
    const publicCheckReason = describeHealthCheckState("public", publicCheckState);
    const privateCheckReason = describeHealthCheckState("private", privateCheckState);

    if (summaryValue === "healthy") {
        return "Public and private checks are healthy.";
    }
    if (summaryValue === "partial") {
        return `${publicCheckReason} ${privateCheckReason}`;
    }
    if (summaryValue === "down") {
        return `${publicCheckReason} ${privateCheckReason}`;
    }
    if (summaryValue === "unconfigured") {
        return "Public and private health checks are both unconfigured.";
    }
    if (summaryValue === "not_checked") {
        return "No health check has run yet.";
    }
    return "Health state is unknown.";
}

function getHostRunnerHealthStatus(hostRecord) {
    return hostRecord.runner_health?.status || "unknown";
}

function setBusyState(isBusy) {
    document.querySelectorAll("button").forEach((buttonElement) => {
        buttonElement.disabled = isBusy;
    });
}

async function readJsonResponse(response) {
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || "Request failed.");
    }
    return payload;
}

function showEmptyDetailState() {
    detailEmptyStateElement.hidden = false;
    projectDetailPanelElement.hidden = true;
    hostDetailPanelElement.hidden = true;
}

function renderDetailViewMode() {
    const showingJson = selectedDetailView === "json";
    const showingDetails = selectedDetailView === "details";

    detailTabProjectViewElement.classList.toggle("is-active", showingDetails);
    detailTabProjectViewElement.setAttribute("aria-selected", String(showingDetails));
    detailTabProjectJsonElement.classList.toggle("is-active", showingJson);
    detailTabProjectJsonElement.setAttribute("aria-selected", String(showingJson));
    detailTabHostViewElement.classList.toggle("is-active", showingDetails);
    detailTabHostViewElement.setAttribute("aria-selected", String(showingDetails));
    detailTabHostJsonElement.classList.toggle("is-active", showingJson);
    detailTabHostJsonElement.setAttribute("aria-selected", String(showingJson));

    projectDetailViewElement.hidden = !showingDetails;
    projectJsonViewElement.hidden = !showingJson;
    hostDetailViewElement.hidden = !showingDetails;
    hostJsonViewElement.hidden = !showingJson;
}

async function requestJson(path, method, payload) {
    const response = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: payload ? JSON.stringify(payload) : undefined,
    });
    return readJsonResponse(response);
}

function setSelectedProject(projectRecord) {
    if (!projectRecord) {
        selectedProjectSlug = "";
        showEmptyDetailState();
        return;
    }

    selectedEntityType = "projects";
    selectedProjectSlug = projectRecord.slug;
    detailEmptyStateElement.hidden = true;
    projectDetailPanelElement.hidden = false;
    hostDetailPanelElement.hidden = true;

    selectedProjectSlugElement.textContent = projectRecord.slug;
    selectedProjectTitleElement.textContent = projectRecord.title;
    selectedProjectDescriptionElement.textContent = projectRecord.description || "No description set.";
    selectedProjectHostElement.textContent = projectRecord.deployment_host || "local";
    selectedProjectRuntimePathElement.textContent = projectRecord.runtime_path || "not set";
    selectedProjectPublicHealthElement.textContent = projectRecord.health_public_url || "not set";
    selectedProjectPrivateHealthElement.textContent = projectRecord.health_private_url || "not set";
    applyStatusBadge(selectedProjectSummaryElement, projectRecord.last_health_summary || "unknown");
    selectedProjectSummaryReasonElement.textContent = buildProjectHealthReason(projectRecord);
    projectJsonEditorElement.value = renderJson(projectRecord);
    renderDetailViewMode();

    projectActionsElement.innerHTML = "";
    supportedActionNames.forEach((actionName) => {
        const actionButtonElement = document.createElement("button");
        actionButtonElement.type = "button";
        actionButtonElement.className = "action-button";
        actionButtonElement.dataset.projectSlug = projectRecord.slug;
        actionButtonElement.dataset.actionName = actionName;
        actionButtonElement.textContent = actionName;
        actionButtonElement.addEventListener("click", () => runProjectAction(projectRecord.slug, actionName));
        projectActionsElement.appendChild(actionButtonElement);
    });

    document.querySelectorAll(".entity-list-button").forEach((entityButtonElement) => {
        const isCurrentSelection =
            entityButtonElement.dataset.entityType === "projects" &&
            entityButtonElement.dataset.entitySlug === projectRecord.slug;
        entityButtonElement.classList.toggle("is-selected", isCurrentSelection);
        entityButtonElement.setAttribute("aria-pressed", String(isCurrentSelection));
    });
}

function setSelectedHost(hostRecord) {
    if (!hostRecord) {
        selectedHostSlug = "";
        showEmptyDetailState();
        return;
    }

    selectedEntityType = "hosts";
    selectedHostSlug = hostRecord.slug;
    detailEmptyStateElement.hidden = true;
    projectDetailPanelElement.hidden = true;
    hostDetailPanelElement.hidden = false;

    selectedHostSlugElement.textContent = hostRecord.slug;
    selectedHostTitleElement.textContent = hostRecord.title;
    selectedHostLocationElement.textContent = hostRecord.location || "No location set.";
    selectedHostRunnerHealthElement.textContent =
        `${getHostRunnerHealthStatus(hostRecord)}${hostRecord.runner_health?.detail ? ` - ${hostRecord.runner_health.detail}` : ""}`;
    selectedHostRunnerUrlElement.textContent = hostRecord.runner_url || "none";
    selectedHostSocketPathElement.textContent = hostRecord.runner_socket_path || "none";
    selectedHostTokenEnvVarElement.textContent = hostRecord.token_env_var || "none";
    selectedHostNotesElement.textContent = hostRecord.notes || "none";
    selectedHostTransportElement.textContent = hostRecord.transport || "none";
    selectedHostTransportElement.className = `status-badge status-badge-${getStatusClassName(getHostRunnerHealthStatus(hostRecord))}`;
    hostJsonEditorElement.value = renderJson(hostRecord);
    renderDetailViewMode();

    document.querySelectorAll(".entity-list-button").forEach((entityButtonElement) => {
        const isCurrentSelection =
            entityButtonElement.dataset.entityType === "hosts" &&
            entityButtonElement.dataset.entitySlug === hostRecord.slug;
        entityButtonElement.classList.toggle("is-selected", isCurrentSelection);
        entityButtonElement.setAttribute("aria-pressed", String(isCurrentSelection));
    });
}

function renderProjectList() {
    entityListElement.innerHTML = "";

    currentProjects.forEach((projectRecord) => {
        const summaryValue = projectRecord.last_health_summary || "unknown";
        const statusClassName = getStatusClassName(summaryValue);
        const entityButtonElement = document.createElement("button");
        const titleElement = document.createElement("span");
        const metaElement = document.createElement("div");
        const summaryTagElement = document.createElement("span");
        const hostTagElement = document.createElement("span");
        const healthReasonElement = document.createElement("div");
        entityButtonElement.type = "button";
        entityButtonElement.className = "entity-list-button";
        entityButtonElement.dataset.entityType = "projects";
        entityButtonElement.dataset.entitySlug = projectRecord.slug;
        titleElement.className = "entity-list-title";
        titleElement.textContent = projectRecord.title;
        metaElement.className = "entity-list-meta";
        summaryTagElement.className = `tag is-${statusClassName}`;
        summaryTagElement.textContent = summaryValue;
        hostTagElement.className = "tag";
        hostTagElement.textContent = projectRecord.deployment_host || "local";
        healthReasonElement.className = "entity-list-health-reason";
        healthReasonElement.textContent = buildProjectHealthReason(projectRecord);
        metaElement.append(summaryTagElement, hostTagElement);
        entityButtonElement.append(titleElement, metaElement, healthReasonElement);
        entityButtonElement.addEventListener("click", () => setSelectedProject(projectRecord));
        entityListElement.appendChild(entityButtonElement);
    });

    const selectedProjectRecord = currentProjects.find((projectRecord) => projectRecord.slug === selectedProjectSlug);
    setSelectedProject(selectedProjectRecord || currentProjects[0] || null);
}

function renderHostList() {
    entityListElement.innerHTML = "";

    currentHosts.forEach((hostRecord) => {
        const entityButtonElement = document.createElement("button");
        const titleElement = document.createElement("span");
        const metaElement = document.createElement("div");
        const transportTagElement = document.createElement("span");
        const runnerHealthTagElement = document.createElement("span");
        entityButtonElement.type = "button";
        entityButtonElement.className = "entity-list-button";
        entityButtonElement.dataset.entityType = "hosts";
        entityButtonElement.dataset.entitySlug = hostRecord.slug;
        titleElement.className = "entity-list-title";
        titleElement.textContent = hostRecord.title;
        metaElement.className = "entity-list-meta";
        transportTagElement.className = "tag";
        transportTagElement.textContent = hostRecord.transport || "none";
        runnerHealthTagElement.className = `tag is-${getStatusClassName(getHostRunnerHealthStatus(hostRecord))}`;
        runnerHealthTagElement.textContent = getHostRunnerHealthStatus(hostRecord);
        metaElement.append(transportTagElement, runnerHealthTagElement);
        entityButtonElement.append(titleElement, metaElement);
        entityButtonElement.addEventListener("click", () => setSelectedHost(hostRecord));
        entityListElement.appendChild(entityButtonElement);
    });

    const selectedHostRecord = currentHosts.find((hostRecord) => hostRecord.slug === selectedHostSlug);
    setSelectedHost(selectedHostRecord || currentHosts[0] || null);
}

function renderSelectedEntityList() {
    selectorTabProjectsElement.classList.toggle("is-active", selectedEntityType === "projects");
    selectorTabProjectsElement.setAttribute("aria-selected", String(selectedEntityType === "projects"));
    selectorTabHostsElement.classList.toggle("is-active", selectedEntityType === "hosts");
    selectorTabHostsElement.setAttribute("aria-selected", String(selectedEntityType === "hosts"));

    if (selectedEntityType === "projects") {
        renderProjectList();
        return;
    }

    renderHostList();
}

async function loadProjects() {
    const payload = await readJsonResponse(await fetch("/projects"));
    currentProjects = payload.projects;
}

async function loadHosts() {
    const payload = await readJsonResponse(await fetch("/hosts"));
    currentHosts = payload.hosts;
}

async function runHealthCheck(projectSlug) {
    try {
        setBusyState(true);
        const payload = await readJsonResponse(
            await fetch(`/projects/${projectSlug}/health-check`, { method: "POST" }),
        );
        setResultPanel(`${projectSlug} health-check`, payload);
        const matchingProjectRecord = currentProjects.find((projectRecord) => projectRecord.slug === projectSlug);
        if (matchingProjectRecord) {
            matchingProjectRecord.last_health_summary = payload.summary;
        }
        renderSelectedEntityList();
    } catch (error) {
        setResultPanel(`${projectSlug} health-check failed`, {
            detail: String(error.message || error),
        });
    } finally {
        setBusyState(false);
    }
}

async function runProjectAction(projectSlug, actionName) {
    try {
        setBusyState(true);
        const payload = await readJsonResponse(
            await fetch(`/projects/${projectSlug}/actions`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: actionName,
                    dry_run: dryRunToggleElement.checked,
                }),
            }),
        );
        setResultPanel(
            `${projectSlug} ${actionName} (${payload.dry_run ? "dry run" : "executed"})`,
            payload,
        );
    } catch (error) {
        setResultPanel(`${projectSlug} ${actionName} failed`, {
            detail: String(error.message || error),
        });
    } finally {
        setBusyState(false);
    }
}

async function refreshDashboard() {
    try {
        setBusyState(true);
        updateDryRunLabel();
        await Promise.all([loadProjects(), loadHosts()]);
        renderSelectedEntityList();
        setResultPanel("Dashboard ready", {
            selected_entity_type: selectedEntityType,
            selected_entity:
                selectedEntityType === "projects" ? selectedProjectSlug || null : selectedHostSlug || null,
            dry_run: dryRunToggleElement.checked,
        });
    } catch (error) {
        setResultPanel("Dashboard load failed", {
            detail: String(error.message || error),
        });
    } finally {
        setBusyState(false);
    }
}

selectorTabProjectsElement.addEventListener("click", () => {
    selectedEntityType = "projects";
    renderSelectedEntityList();
});

selectorTabHostsElement.addEventListener("click", () => {
    selectedEntityType = "hosts";
    renderSelectedEntityList();
});

detailTabProjectViewElement.addEventListener("click", () => {
    selectedDetailView = "details";
    renderDetailViewMode();
});

detailTabProjectJsonElement.addEventListener("click", () => {
    selectedDetailView = "json";
    renderDetailViewMode();
});

detailTabHostViewElement.addEventListener("click", () => {
    selectedDetailView = "details";
    renderDetailViewMode();
});

detailTabHostJsonElement.addEventListener("click", () => {
    selectedDetailView = "json";
    renderDetailViewMode();
});

healthCheckButtonElement.addEventListener("click", () => {
    if (selectedProjectSlug) {
        runHealthCheck(selectedProjectSlug);
    }
});

projectJsonSaveButtonElement.addEventListener("click", async () => {
    if (!selectedProjectSlug) {
        return;
    }
    try {
        setBusyState(true);
        const projectPayload = JSON.parse(projectJsonEditorElement.value);
        const responsePayload = await requestJson(`/projects/${selectedProjectSlug}`, "PUT", projectPayload);
        selectedProjectSlug = responsePayload.project.slug;
        await loadProjects();
        renderSelectedEntityList();
        selectedDetailView = "details";
        renderDetailViewMode();
        setResultPanel(`Saved project ${responsePayload.project.slug}`, responsePayload);
    } catch (error) {
        setResultPanel(`Failed to save project ${selectedProjectSlug}`, { detail: String(error.message || error) });
    } finally {
        setBusyState(false);
    }
});

projectJsonResetButtonElement.addEventListener("click", () => {
    const projectRecord = currentProjects.find((candidateProjectRecord) => candidateProjectRecord.slug === selectedProjectSlug);
    if (projectRecord) {
        projectJsonEditorElement.value = renderJson(projectRecord);
    }
});

projectDeleteButtonElement.addEventListener("click", async () => {
    if (!selectedProjectSlug) {
        return;
    }
    try {
        setBusyState(true);
        const deletedProjectSlug = selectedProjectSlug;
        const responsePayload = await requestJson(`/projects/${deletedProjectSlug}`, "DELETE");
        selectedProjectSlug = "";
        await loadProjects();
        renderSelectedEntityList();
        setResultPanel(`Deleted project ${deletedProjectSlug}`, responsePayload);
    } catch (error) {
        setResultPanel(`Failed to delete project ${selectedProjectSlug}`, { detail: String(error.message || error) });
    } finally {
        setBusyState(false);
    }
});

hostJsonSaveButtonElement.addEventListener("click", async () => {
    if (!selectedHostSlug) {
        return;
    }
    try {
        setBusyState(true);
        const hostPayload = JSON.parse(hostJsonEditorElement.value);
        const responsePayload = await requestJson(`/hosts/${selectedHostSlug}`, "PUT", hostPayload);
        selectedHostSlug = responsePayload.host.slug;
        await loadHosts();
        renderSelectedEntityList();
        selectedDetailView = "details";
        renderDetailViewMode();
        setResultPanel(`Saved host ${responsePayload.host.slug}`, responsePayload);
    } catch (error) {
        setResultPanel(`Failed to save host ${selectedHostSlug}`, { detail: String(error.message || error) });
    } finally {
        setBusyState(false);
    }
});

hostJsonResetButtonElement.addEventListener("click", () => {
    const hostRecord = currentHosts.find((candidateHostRecord) => candidateHostRecord.slug === selectedHostSlug);
    if (hostRecord) {
        hostJsonEditorElement.value = renderJson(hostRecord);
    }
});

hostDeleteButtonElement.addEventListener("click", async () => {
    if (!selectedHostSlug) {
        return;
    }
    try {
        setBusyState(true);
        const deletedHostSlug = selectedHostSlug;
        const responsePayload = await requestJson(`/hosts/${deletedHostSlug}`, "DELETE");
        selectedHostSlug = "";
        await loadHosts();
        renderSelectedEntityList();
        setResultPanel(`Deleted host ${deletedHostSlug}`, responsePayload);
    } catch (error) {
        setResultPanel(`Failed to delete host ${selectedHostSlug}`, { detail: String(error.message || error) });
    } finally {
        setBusyState(false);
    }
});

dryRunToggleElement.addEventListener("change", updateDryRunLabel);

updateDryRunLabel();
refreshDashboard();
