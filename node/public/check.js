let currentSummary = ""; // 요약을 저장할 전역 변수
let date = "";

flatpickr("#calendar", {
  inline: true, // 달력을 항상 열려 있도록 설정
  onChange: async function (selectedDates, dateStr, instance) {
    const selectedDateElement = document.getElementById("selected-date");
    selectedDateElement.innerText = `${dateStr}`;
    // 대화 요약본 가져오는 코드
    const summaryContainer = document.getElementById("summary-container");
    const summaryContent = document.getElementById("summary-content");
    // AJAX 요청 등을 통해 선택된 날짜에 해당하는 대화 요약본을 가져오는 코드
    await fetchSummarySpeech(dateStr);
    if(currentSummary!="대화 기록이 없어요"){
        summaryContent.innerText = currentSummary;
    }
    summaryContainer.style.display = "flex";
    // 오디오 가져오는 코드
    const formattedDate = dateStr.split("-").join("");
    const audioSource = document.getElementById("audioSource");
    audioSource.src = `http://43.203.206.180:3500/audio/${formattedDate}`;
    const audio = document.getElementById("audio");
    audio.load();

    audio.addEventListener("canplay", function autoPlay() {
      audio
        .play()
        .then(() => {
          audio.removeEventListener("canplay", autoPlay);
        })
        .catch((error) => {
          console.error("Error playing audio:", error);
        });
    });
    playPauseCheckbox.checked = true;
  },
});

async function fetchSummary(selectedDate) {
  try {
    let summary;
    const currentDate = new Date().toISOString().split("T")[0]; // 오늘의 날짜 가져오기
    const selectedDateOnly = selectedDate.split("T")[0]; // 선택한 날짜에서 시간 정보 제거
    const summaryContainer = document.getElementById('summary-content');
    const noSummaryImage = document.getElementById('no-summary-image');

    // 기존 내용을 제거하여 초기 상태로 설정
    summaryContainer.innerHTML = '';
    noSummaryImage.style.display = 'none';

    if (selectedDateOnly === currentDate) {
      // 오늘의 날짜인 경우 /getchatfroms3 엔드포인트 호출
      const response = await fetch(
        `http://3.36.52.133:3000/getchatfroms3?file_name=chat_log_${selectedDate}.json`
      );
      const data = await response.json();
      if (data.error) {
        summary = "대화 기록이 없어요"; // 에러 메시지 반환
        noSummaryImage.style.display = 'block'; // 이미지 표시
      } else {
        // 반환된 데이터를 JSON 형식으로 파싱
        const parsedData = JSON.parse(data);

        // "chat" 속성의 값이 배열인지 확인
        if (Array.isArray(parsedData.chat)) {
          // "chat" 배열의 각 항목에 접근하여 필요한 정보 추출
          const chatEntries = parsedData.chat.map(
            (entry) => `사용자: ${entry.message} \n 챗봇 : ${entry.response}`
          );

          // 각 채팅 엔트리를 개행 문자로 연결하여 문자열로 변환
          summary = chatEntries.join("\n\n");
        } else {
          summary = "데이터 형식이 올바르지 않습니다.";
        }
      }
    } else {
      // 오늘의 날짜가 아닌 경우 /getsummaryfroms3 엔드포인트 호출
      const response = await fetch(
        `http://3.36.52.133:3000/getsummaryfroms3?file_name=chat_log_${selectedDate}.json`
      );
      const data = await response.json();
      console.log("getsummaryfroms3 response:", data);

      if (data.error) {
        // S3에 파일이 없을 경우 /summarizechat 엔드포인트 호출
        const summarizeResponse = await fetch(
          `http://3.36.52.133:3000/summarizechat?file_name=chat_log_${selectedDate}.json`
        );
        const summaryData = await summarizeResponse.json();
        console.log("summarizechat response:", summaryData);

        if (summaryData.error) {
            summary = '대화 기록이 없어요'; // 에러 메시지 반환
            noSummaryImage.style.display = 'block'; // 이미지 표시
        } else {
          if (Array.isArray(summaryData.summary)) {
            // 배열을 개행 문자로 연결하여 문자열로 변환하여 반환
            summary = summaryData.summary.join("\n");
          } else {
            summary = summaryData.summary; // summary가 배열이 아닌 경우 그대로 반환
          }
        }
      } else {
        if (Array.isArray(data.summary)) {
          // 배열을 개행 문자로 연결하여 문자열로 변환하여 반환
          summary = data.summary.join("\n");
        } else {
          summary = data.summary; // summary가 배열이 아닌 경우 그대로 반환
        }
      }
    }

    return summary;
  } catch (error) {
    console.error("요약을 가져오는 중 오류 발생:", error);
    return "선택한 날짜의 요약을 가져오는 데 실패했습니다.";
  }
}

// Summary 를 TTS로 저장
async function fetchSummarySpeech(selectedDate) {
  const selectedDateOnly = selectedDate.split("T")[0]; // 선택한 날짜에서 시간 정보 제거
  date = selectedDate.split("-").join("");
  currentSummary = await fetchSummary(selectedDateOnly);
  const summary = currentSummary;
  try {
    const response = await fetch("/texttospeech", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ summary: currentSummary, datestr:date }),
    });

    if (!response.ok) {
      throw new Error("Failed to send summary to text-to-speech service");
    }

    console.log("Summary sent to text-to-speech service");
  } catch (error) {
    console.error("Error sending summary to text-to-speech service:", error);
  }
}

// 오디오 재생 및 멈춤 처리
const audio = document.getElementById("audio");
const playPauseCheckbox = document.getElementById("playPauseCheckbox");

playPauseCheckbox.addEventListener("change", () => {
  if (playPauseCheckbox.checked) {
    audio.play().catch((error) => {
      console.error("Failed to play audio:", error);
    });
  } else {
    audio.pause();
  }
});
