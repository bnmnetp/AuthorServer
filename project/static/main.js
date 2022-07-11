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
    let bcname = document.querySelector("#bcname");
    fetch("/clone", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: repo.value, bcname: bcname.value }),
    })
        .then((response) => response.json())
        .then((data) => {
            getStatus(data.task_id);
        });
}

// see checkDB in main.py
async function checkDB(el) {
    let response = await fetch("/book_in_db", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ bcname: el.value }),
    });
    if (response.ok) {
        let data = await response.json();
        if (data.detail == true) {
            alert("book is there");
            // add a check next to add book to database and disable that button
        }
    }
}

// see new_course in main.py
async function addCourse() {
    let bcname = document.querySelector("#bcname");
    let response = await fetch("/add_course", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ bcname: bcname.value }),
    });
    if (response.ok) {
        let data = await response.json();
        if (data.detail == "success") {
            alert("book is there");
            // add a check next to add book to database and disable that button
        }
    }
}

// This checks on the task status from a previously scheduled task.
// todo: how to report the status better
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
