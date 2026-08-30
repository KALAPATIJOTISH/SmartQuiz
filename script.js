/* =========================================
   SMARTQUIZ - MAIN JAVASCRIPT
========================================= */


/* =========================================
   MOBILE NAVIGATION MENU
========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const menuToggle = document.querySelector(".menu-toggle");
    const navLinks = document.querySelector(".nav-links");

    if (menuToggle && navLinks) {

        menuToggle.addEventListener("click", function () {

            navLinks.classList.toggle("active");

        });

    }


    /* =========================================
       AUTO CLOSE FLASH MESSAGES
    ========================================= */

    const flashMessages = document.querySelectorAll(".flash-message");

    flashMessages.forEach(function (message) {

        const closeButton = message.querySelector(".close-flash");

        if (closeButton) {

            closeButton.addEventListener("click", function () {

                message.style.opacity = "0";

                setTimeout(function () {
                    message.remove();
                }, 300);

            });

        }


        /* Automatically disappear after 5 seconds */

        setTimeout(function () {

            if (message.parentNode) {

                message.style.opacity = "0";

                setTimeout(function () {
                    message.remove();
                }, 300);

            }

        }, 5000);

    });


    /* =========================================
       QUIZ PROGRESS TRACKING
    ========================================= */

    const quizForm = document.getElementById("quizForm");

    const progressFill = document.getElementById("progressFill");

    const progressText = document.getElementById("progressText");


    if (quizForm && progressFill && progressText) {

        const questions = quizForm.querySelectorAll(
            ".quiz-question-card"
        );

        const totalQuestions = questions.length;


        const radioButtons = quizForm.querySelectorAll(
            'input[type="radio"]'
        );


        radioButtons.forEach(function (radio) {

            radio.addEventListener("change", function () {

                updateProgress();

            });

        });


        function updateProgress() {

            let answeredQuestions = 0;


            questions.forEach(function (question) {

                const selected = question.querySelector(
                    'input[type="radio"]:checked'
                );

                if (selected) {
                    answeredQuestions++;
                }

            });


            const percentage =
                (answeredQuestions / totalQuestions) * 100;


            progressFill.style.width = percentage + "%";


            progressText.textContent =
                answeredQuestions +
                " / " +
                totalQuestions;

        }

    }


    /* =========================================
       QUIZ SUBMIT CONFIRMATION
    ========================================= */

    if (quizForm) {

        quizForm.addEventListener("submit", function (event) {

            const questions = quizForm.querySelectorAll(
                ".quiz-question-card"
            );

            let answeredQuestions = 0;


            questions.forEach(function (question) {

                const selected = question.querySelector(
                    'input[type="radio"]:checked'
                );

                if (selected) {
                    answeredQuestions++;
                }

            });


            const totalQuestions = questions.length;


            if (answeredQuestions < totalQuestions) {

                const unanswered =
                    totalQuestions - answeredQuestions;


                const confirmSubmit = confirm(
                    "You still have " +
                    unanswered +
                    " unanswered question(s). Do you want to submit anyway?"
                );


                if (!confirmSubmit) {

                    event.preventDefault();

                }

            }

        });

    }


    /* =========================================
       SMOOTH BUTTON ANIMATION
    ========================================= */

    const buttons = document.querySelectorAll(".btn");

    buttons.forEach(function (button) {

        button.addEventListener("mousedown", function () {

            button.style.transform = "scale(0.97)";

        });


        button.addEventListener("mouseup", function () {

            button.style.transform = "";

        });


        button.addEventListener("mouseleave", function () {

            button.style.transform = "";

        });

    });

});