// custom javascript

(function () {
    console.log("Sanity Check!");
})();

function handleClick(type) {
    fetch("/tasks", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ type: type }),
    })
        .then((response) => response.json())
        .then((data) => {
            getStatus(data.task_id);
        });
}

// Trigger the task to clone a given repo.
// This task is implemented in worker.py
//
function cloneTask() {
    let repo = document.querySelector("#gitrepo");
    fetch("/clone", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: repo.value }),
    })
        .then((response) => response.json())
        .then((data) => {
            getStatus(data.task_id);
        });
}

function getStatus(taskID) {
    fetch(`/tasks/${taskID}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    })
        .then((response) => response.json())
        .then((res) => {
            console.log(res);
            const html = `
      <tr>
        <td>${taskID}</td>
        <td>${res.task_status}</td>
        <td>${res.task_result.current}</td>
      </tr>`;
            const newRow = document.getElementById("tasks").insertRow(0);
            newRow.innerHTML = html;

            const taskStatus = res.task_status;
            if (taskStatus === "SUCCESS" || taskStatus === "FAILURE")
                return false;
            setTimeout(function () {
                getStatus(res.task_id);
            }, 1000);
        })
        .catch((err) => console.log(err));
}
