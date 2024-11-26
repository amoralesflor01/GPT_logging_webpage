// To prevent navigation to cached pages using the back button
window.history.pushState(null, "", window.location.href);
window.onpopstate = function () {
  window.history.pushState(null, "", window.location.href);
};

// To prevent back navigation on the survey page
if (window.location.pathname.includes("survey")) {
    window.history.pushState(null, "", window.location.href);
    window.onpopstate = function () {
        window.history.pushState(null, "", window.location.href);
    };
}


(function () {
  var Message;
  // Constructor Function
  Message = function (arg) {
    (this.text = arg.text), (this.message_side = arg.message_side);
    this.draw = (function (_this) {
      return function () {
        var $message;
        $message = $($(".message_template").clone().html());
        $message.addClass(_this.message_side).find(".text").html(_this.text);
        $(".messages").append($message);
        // Timeout function required to activate transition animation css
        return setTimeout(function () {
          return $message.addClass("appeared");
        }, 0);
      };
    })(this);
    return this;
  };

  // $(function... means when the doc is ready
  // shorthand for $(document).ready(function() { ... });
  $(function () {
    var getMessageText, message_side, sendMessage;
    message_side = "right";

    // Helper Function getMessageText
    getMessageText = function () {
      // retreives user inputs from the class message_input
      var $message_input;
      $message_input = $(".message_input"); // text box class
      return $message_input.val();
    };

    // Helper Function scrollToBottom
    function scrollToBottom() {
      var $messages;
      $messages = $(".messages"); // select the entire unordered list (initially empty)
      $messages.animate(
        {
          scrollTop: $messages.prop("scrollHeight"),
        },
        300
      );
    }

    // Helper Function sendMessage
    sendMessage = function (text) {
      // This function handles readies the msg for gpt
      var message;
      if (text.trim() === "") {
        return;
      }
      $(".message_input").val(""); // empties the input chat box

      // Set message_side based on whether the message is from the user or chatbot

      var message_side = "right"; // User
      message = new Message({
        text: text,
        message_side: message_side,
      });
      // Draw user message
      message.draw();

      // Call getResponse() to get the chatbot's response
      $.get("/get", {
        msg: text,
      }).done(function (data) {
        var botMessage = new Message({
          text: data,
          message_side: "left",
        });

        // Draw bot message
        botMessage.draw();
        scrollToBottom();
      });

      return scrollToBottom();
    };

    // Monitoring the send button
    $(".send_message").click(function (e) {
      return sendMessage(getMessageText());
    });

    // Monitoring if Enter button is pressed
    $(".message_input").keyup(function (e) {
      if (e.which === 13) {
        return sendMessage(getMessageText());
      }
    });

    // Runs once to send the inital bot message. (MOVED TO APP.PY)
    /*var userId = $('#userInfo').data('userid');
        writingMessage = new Message({
            text: 'Hey, I am a ChatBot. I am designed to help you with identifying Spam and Phishing emails/sms. I support English and Spanish. Please feel free to ask me anything! Your UserID is ' + userId,
            message_side: 'left'
        });
        writingMessage.draw();*/
    scrollToBottom();

    //-----------------------

    // @Sadrac Work Button
    // Function to terminate the session
    function endSession() {
      // Show alert before session ends
      alert(
        "Chat Session has terminated. You will be proceeded to take the survey."
      );

      // Redirect to the session ending logic or login page
      window.location.href = "/end-chat-session"; // This should match the logic for session termination
    }

    //Search Bar
    document
      .querySelector(".gmail-search-bar")
      .addEventListener("focus", function (event) {
        event.preventDefault(); // Prevent focus
      });

    // Attach event listener to the "End Session" button
    document
      .getElementById("end-session-btn")
      .addEventListener("click", function () {
        endSession();
      });
  });
}).call(this);

("use strict");

$(function () {
  $("body");

  $("input[type='password'][data-eye]").each(function (i) {
    var $this = $(this),
      id = "eye-password-" + i,
      el = $("#" + id);

    $this.wrap(
      $("<div/>", {
        style: "position:relative",
        id: id,
      })
    );

    $this.css({
      paddingRight: 60,
    });
    $this.after(
      $("<div/>", {
        html: "Show",
        class: "btn btn-primary btn-sm",
        id: "passeye-toggle-" + i,
      }).css({
        position: "absolute",
        right: 10,
        top: $this.outerHeight() / 2 - 12,
        padding: "2px 7px",
        fontSize: 12,
        cursor: "pointer",
      })
    );

    $this.after(
      $("<input/>", {
        type: "hidden",
        id: "passeye-" + i,
      })
    );

    var invalid_feedback = $this.parent().parent().find(".invalid-feedback");

    if (invalid_feedback.length) {
      $this.after(invalid_feedback.clone());
    }

    $this.on("keyup paste", function () {
      $("#passeye-" + i).val($(this).val());
    });
    $("#passeye-toggle-" + i).on("click", function () {
      if ($this.hasClass("show")) {
        $this.attr("type", "password");
        $this.removeClass("show");
        $(this).removeClass("btn-outline-primary");
      } else {
        $this.attr("type", "text");
        $this.val($("#passeye-" + i).val());
        $this.addClass("show");
        $(this).addClass("btn-outline-primary");
      }
    });
  });

  $(".my-login-validation").submit(function () {
    var form = $(this);
    if (form[0].checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    form.addClass("was-validated");
  });
});
