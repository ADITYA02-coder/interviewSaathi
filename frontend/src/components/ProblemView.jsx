export default function ProblemView({ problem }) {
  if (!problem) return null;
  return (
    <div className="prob">
      <div className="prob-head"><h3>{problem.title}</h3><span className={`pill ${problem.difficulty === "easy" ? "green" : problem.difficulty === "medium" ? "gold" : "coral"}`}>{problem.difficulty}</span><span className="pill">{problem.topic}</span></div>
      <p>{problem.statement}</p>
      <div className="fmt"><div><span className="label">Input</span><pre>{problem.input_format}</pre></div><div><span className="label">Output</span><pre>{problem.output_format}</pre></div></div>
      {problem.examples?.map((e, i) => (
        <div className="fmt ex" key={i}><div><span className="label">Example {i + 1} input</span><pre>{e.input}</pre></div><div><span className="label">Output</span><pre>{e.output}</pre></div></div>))}
    </div>
  );
}
