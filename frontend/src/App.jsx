import { useState } from "react";

function App() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);

  const processDPR = async () => {
    const response = await fetch("http://127.0.0.1:8000/process-dpr", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
      }),
    });

    const data = await response.json();
    setResult(data);
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Arial" }}>
      <h1>SIH26122 Progress Linking</h1>

      <h3>Enter Site Progress Report</h3>

      <textarea
        rows="6"
        cols="60"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Example: F101 concreting completed today."
      />

      <br />
      <br />

      <button onClick={processDPR}>
        Process DPR
      </button>

      {result && (
        <div style={{ marginTop: "30px" }}>
          <h3>Backend Response</h3>

          <pre>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default App;