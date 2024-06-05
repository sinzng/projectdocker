window.onload = function () {
  console.log("fired");
    if (typeof webkitSpeechRecognition !== "function") {
      alert("크롬에서만 동작 합니다.");
      return false;
    }
    const recognition = new window.webkitSpeechRecognition();
    const language = "ko-KR";
    const micBtn = document.querySelector(".mic");
    const resultWrap = document.querySelector(".result");
    const userInput = document.querySelector("#user-input input");
    const recording_state = document.querySelector("#recording-state");
    const interim_span = document.querySelector("#interim_span");
  
    let isRecognizing = false;
    let ignoreEndProcess = false;
    let finalTranscript = "";
  
    recognition.continuous = true;
    recognition.interimResults = true;
    // interimResults = false => return first word
  
    // 음성 인식 시작
    recognition.onstart = function (event) {
      console.log("onstart", event);
      isRecognizing = true;
      userInput.placeholder = "";
      recording_state.classList.add("on");
    };
  
    // 음성 인식 종료
    recognition.onend = function () {
      console.log("onend", arguments);
      isRecognizing = false;
  
      if (ignoreEndProcess) {
        return false;
      }
  
      // Do end process
      recording_state.classList.remove("on");
      console.log("off");
      if (!finalTranscript) {
        console.log("empty finalTranscript");
        return false;
      }
    };
  
    // 음성 인식 결과
    recognition.onresult = function (event) {
      console.log("onresult", event);
  
      let finalTranscript = ""; // 음성 인식된 내용 초기화
      let interimTranscript = "";
      if (typeof event.results === "undefined") {
        recognition.onend = null;
        recognition.stop();
        return;
      }
  
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }
  
      userInput.value = finalTranscript;
      interim_span.textContent = interimTranscript;
  
      console.log("finalTranscript", finalTranscript);
      console.log("interimTranscript", interimTranscript);
      // fireCommand(interimTranscript);
    };
  
    // 음성 인식 에러
    recognition.onerror = function (event) {
      console.log("onerror", event);
  
      if (event.error.match(/no-speech|audio-capture|not-allowed/)) {
        ignoreEndProcess = true;
      }
  
      micBtn.classList.add();
    };
  
    // .mic 버튼 클릭시
    function start() {
      if (isRecognizing) {
        // 종료
        recognition.stop();
        console.log("stopped");
        return;
      }
      recognition.lang = language;
      recognition.start(); // 음성 인식 시작
      ignoreEndProcess = false;
  
      finalTranscript = "";
      interim_span.innerHTML = "";
    }
    /**
     * 초기 바인딩
     */
    function resultWordHandler(event) {
      console.log("clicked id : " + event.target.value);
    }
  
    function initialize() {
      micBtn.addEventListener("click", start);
      //마이크 버튼 누르면 시작
    }
  
    initialize();


const chatMessages = document.querySelector("#chat-messages");
const sendButton = document.querySelector(
".buttons-container .send-button"
);

function addMessage(sender, message) {
const messageElement = document.createElement("div");
messageElement.className = `message ${sender}`;
messageElement.textContent = message;
chatMessages.prepend(messageElement);
}

async function fetchAIResponse(prompt) {
const response = await fetch("http://3.36.52.133:3000/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message: prompt }),
});

const data = await response.json();

if (data.error) {
  throw new Error(data.error);
}

return data.response;
}

sendButton.addEventListener("click", async () => {
  const message = userInput.value.trim();
  if (message.length === 0) return;
  addMessage("user", message);
  userInput.value = "";
  userInput.placeholder = "메시지를 입력하세요...";
  try {
    const aiResponse = await fetchAIResponse(message);
    addMessage("bot", aiResponse);
  } catch (error) {
    addMessage("bot", `오류 발생: ${error.message}`);
  }
});

userInput.addEventListener("keydown", (event) => {
if (event.key === "Enter") {
  sendButton.click();
}
});

const startButton = document.getElementById('start');
startButton.addEventListener('click', () => {
  const chatContainer = document.getElementById('chat-container');
  if (chatContainer.style.visibility === 'hidden' || chatContainer.style.visibility === '') {
    chatContainer.style.visibility = 'visible';
  } else {
    chatContainer.style.visibility = 'hidden';
  }
});


};