import { useState } from 'react';
export function QuizQuestion({ question, options, value, onChange }) {
  const [internal, setInternal] = useState(null);
  const selected = value === undefined ? internal : value;
  const choose = option => {
    const answer = typeof option === 'string' ? option : option.value;
    setInternal(answer);
    onChange?.(answer);
  };
  return <fieldset className="answer-options"><legend>{question}</legend>{options.map(option => {
    const answer = typeof option === 'string' ? option : option.value;
    const label = typeof option === 'string' ? option : option.label;
    return <label className={selected === answer ? 'selected' : ''} key={answer}><input type="radio" name="quiz-question" checked={selected === answer} onChange={() => choose(typeof option === 'string' ? option : { ...option, value: answer })}/><span>{label}</span></label>;
  })}</fieldset>;
}
