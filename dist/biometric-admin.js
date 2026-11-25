
(function () {
    const localHosts = ["127.0.0.1", "localhost", "[::1]"];

    if (!localHosts.includes(window.location.hostname)) {
        return;
    }

    const panel = document.getElementById("bio-admin-panel");
    const form = document.getElementById("bio-admin-form");
    const passwordInput = document.getElementById("bio-admin-password");
    const loginButton = document.getElementById("bio-admin-login-button");
    const logoutButton = document.getElementById("bio-admin-logout");
    const status = document.getElementById("bio-admin-status");

    if (!panel || !form || !status) {
        return;
    }


    // PALMA PALM VERIFICATION UI
    const verifyId = document.getElementById("bio-verify-id");
    const verifyImage = document.getElementById("bio-verify-image");
    const verifyCard = verifyId.closest(".biometric-tool-card");
    const verifyButton = verifyCard.querySelector("button");
    const oldNote = verifyCard.querySelector(".biometric-note");

    const verifyStatus = document.createElement("p");
    verifyStatus.setAttribute("role", "status");
    verifyStatus.setAttribute("aria-live", "polite");
    verifyStatus.className = "biometric-note";
    verifyButton.insertAdjacentElement("afterend", verifyStatus);

    if (oldNote) {
        oldNote.textContent = "Authorized local testing only.";
    }

    let adminAuthenticated = false;

    // PALMA SECURE ENROLLMENT SUBMISSION

    const enrollId = document.getElementById("bio-enroll-id");
    const enrollImages = document.getElementById("bio-enroll-images");
    const enrollHand = document.getElementById("bio-enroll-hand-side");
    const enrollConsent = document.querySelector(
        ".biometric-consent input[type='checkbox']"
    );

    const enrollCard = enrollId.closest(".biometric-tool-card");
    const enrollButton = enrollCard.querySelector("button");
    const enrollNote = enrollCard.querySelector(".biometric-note");

    const enrollStatus = document.createElement("p");
    enrollStatus.className = "biometric-note";
    enrollStatus.setAttribute("role", "status");
    enrollStatus.setAttribute("aria-live", "polite");

    enrollButton.insertAdjacentElement("afterend", enrollStatus);

    if (enrollNote) {
        enrollNote.textContent =
            "Authorized local enrollment with participant consent.";
    }

    let enrollmentBusy = false;

    function enrollmentFormValid() {
        const id = enrollId.value.trim();
        const hand = enrollHand.value;
        const files = Array.from(enrollImages.files || []);

        return (
            /^[A-Za-z0-9_-]{1,40}$/.test(id) &&
            ["left", "right"].includes(hand) &&
            files.length === 3 &&
            files.every(file =>
                file.size > 0 &&
                file.size <= 5 * 1024 * 1024 &&
                ["image/jpeg", "image/png"].includes(file.type)
            ) &&
            enrollConsent.checked
        );
    }

    function updateEnrollmentButton() {
        enrollButton.disabled = (
            !adminAuthenticated ||
            enrollmentBusy ||
            !enrollmentFormValid()
        );
    }

    enrollId.addEventListener("input", updateEnrollmentButton);
    enrollHand.addEventListener("change", updateEnrollmentButton);
    enrollImages.addEventListener("change", updateEnrollmentButton);
    enrollConsent.addEventListener("change", updateEnrollmentButton);

    enrollButton.addEventListener("click", async function () {
        if (
            !adminAuthenticated ||
            !csrfToken ||
            !enrollmentFormValid() ||
            enrollmentBusy
        ) {
            enrollStatus.textContent =
                "Complete the form and sign in as admin.";
            return;
        }

        const confirmed = window.confirm(
            "Confirm that the participant has provided informed " +
            "consent to store encrypted biometric templates. Continue?"
        );

        if (!confirmed) {
            return;
        }

        const formData = new FormData();

        formData.append("user_id", enrollId.value.trim());
        formData.append("hand_side", enrollHand.value);
        formData.append("consent", "true");

        for (const file of enrollImages.files) {
            formData.append("images", file);
        }

        enrollmentBusy = true;
        updateEnrollmentButton();

        enrollStatus.textContent =
            "Processing three palm images. Please do not close this page.";

        try {
            const response = await fetch(
                "/api/biometric/enroll",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRF-Token": csrfToken
                    },
                    body: formData
                }
            );

            const data = await response.json().catch(
                () => ({ error: "Unexpected server response" })
            );

            if (!response.ok) {
                enrollStatus.textContent =
                    data.detail || data.error ||
                    "Enrollment could not be completed.";
                return;
            }

            enrollStatus.textContent =
                "Enrollment Successful! Participant: " +
                data.user_id +
                " | Templates saved: " +
                data.template_count;

            enrollId.value = "";
            enrollHand.value = "";
            enrollImages.value = "";
            enrollConsent.checked = false;

        } catch (error) {
            enrollStatus.textContent =
                "Could not connect to the enrollment service.";
        } finally {
            enrollmentBusy = false;
            updateEnrollmentButton();
        }
    });

    updateEnrollmentButton();



    let csrfToken = "";
    panel.hidden = false;

    function showAuthenticated(authenticated) {
        form.hidden = authenticated;
        logoutButton.hidden = !authenticated;

        adminAuthenticated = authenticated;
        updateEnrollmentButton();

        // PALMA ENROLLMENT INPUT FIX
        const enrollId = document.getElementById("bio-enroll-id");
        const enrollImages = document.getElementById("bio-enroll-images");
        const enrollConsent = document.querySelector(
            ".biometric-consent input[type='checkbox']"
        );

        if (enrollId) {
            enrollId.disabled = !authenticated;
        }

        const enrollHandSide = document.getElementById(
            "bio-enroll-hand-side"
        );

        if (enrollHandSide) {
            enrollHandSide.disabled = !authenticated;
        }

        if (enrollImages) {
            enrollImages.disabled = !authenticated;
        }

        if (enrollConsent) {
            enrollConsent.disabled = !authenticated;
        }

        verifyId.disabled = !authenticated;
        verifyImage.disabled = !authenticated;
        verifyButton.disabled = !authenticated;

        verifyStatus.textContent = authenticated
            ? "Ready to verify a palm image."
            : "Sign in as admin to enable verification.";


        status.textContent = authenticated
            ? "Admin authenticated. Secure testing access is active."
            : "Please sign in to access biometric testing.";
    }

    async function loadSession() {
        const response = await fetch(
            "/api/biometric/admin/session",
            {
                credentials: "same-origin",
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error("Session check failed");
        }

        const data = await response.json();
        csrfToken = data.csrf_token || "";
        showAuthenticated(data.authenticated === true);
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        if (!csrfToken) {
            status.textContent = "Session unavailable. Refresh the page.";
            return;
        }

        loginButton.disabled = true;
        status.textContent = "Checking credentials...";

        const password = passwordInput.value;

        try {
            const response = await fetch(
                "/api/biometric/admin/login",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRF-Token": csrfToken
                    },
                    body: JSON.stringify({ password: password })
                }
            );

            const data = await response.json();
            passwordInput.value = "";

            if (!response.ok) {
                status.textContent = data.error || "Login failed.";
                return;
            }

            csrfToken = data.csrf_token || "";
            showAuthenticated(true);

        } catch (error) {
            passwordInput.value = "";
            status.textContent = "Could not connect to the server.";
        } finally {
            loginButton.disabled = false;
        }
    });

    logoutButton.addEventListener("click", async function () {
        logoutButton.disabled = true;

        try {
            const response = await fetch(
                "/api/biometric/admin/logout",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRF-Token": csrfToken
                    }
                }
            );

            if (!response.ok) {
                throw new Error("Logout failed");
            }

            csrfToken = "";
            await loadSession();

        } catch (error) {
            status.textContent = "Could not sign out. Try again.";
        } finally {
            logoutButton.disabled = false;
        }
    });


    verifyButton.addEventListener("click", async function () {
        if (!adminAuthenticated || !csrfToken) {
            verifyStatus.textContent = "Admin login required.";
            return;
        }

        const userId = verifyId.value.trim();
        const imageFile = verifyImage.files[0];

        if (!/^[A-Za-z0-9_-]{1,40}$/.test(userId)) {
            verifyStatus.textContent =
                "Enter a valid participant ID.";
            return;
        }

        if (!imageFile) {
            verifyStatus.textContent =
                "Please select one palm image.";
            return;
        }

        if (
            imageFile.size === 0 ||
            imageFile.size > 8 * 1024 * 1024 ||
            !["image/jpeg", "image/png"].includes(imageFile.type)
        ) {
            verifyStatus.textContent =
                "Choose a JPG or PNG image under 8 MB.";
            return;
        }

        const formData = new FormData();
        formData.append("user_id", userId);
        formData.append("image", imageFile);

        verifyButton.disabled = true;
        verifyStatus.textContent = "Processing palm verification...";

        try {
            const response = await fetch(
                "/api/biometric/verify",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRF-Token": csrfToken
                    },
                    body: formData
                }
            );

            const data = await response.json();

            if (!response.ok) {
                verifyStatus.textContent =
                    data.error ||
                    data.message ||
                    "Verification could not be completed.";
                return;
            }

            let resultText = data.status || "Verification completed";

            if (typeof data.score === "number") {
                resultText +=
                    " | Similarity: " + data.score.toFixed(4);
            }

            verifyStatus.textContent = resultText;

        } catch (error) {
            verifyStatus.textContent =
                "Could not complete verification. Check the server.";
        } finally {
            verifyButton.disabled = !adminAuthenticated;
        }
    });

    loadSession().catch(function () {
        status.textContent =
            "Admin service unavailable. Restart the Flask server.";
        form.hidden = true;
    });
})();
