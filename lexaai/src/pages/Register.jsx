import "../styles/register.css"
import { Scale } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import axios from "axios";


export default function Register() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleRegister = async () => {
    const response = await axios.post(
      "http://127.0.0.1:8000/register",
      {
        name,
        email,
        password,
      }
    );


};



  return (
    <div className="register-container">
      <div className="register-card">
        <div className="register-header">
          <div className="logo-circle">
            <Scale size={28} />
          </div>

          <h1>LexaAI</h1>

          <p>Create your account</p>
        </div>

        <div className="register-form">
          <input
            type="text"
            placeholder="Full Name"
            value={name}
            onChange={(e) =>
              setName(e.target.value)
            }
          />

          <input
            type="email"
            placeholder="Email Address"
            value={email}
            onChange={(e) =>
              setEmail(e.target.value)
            }
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) =>
              setPassword(e.target.value)
            }
          />

          <button onClick={handleRegister}>
            Create Account
          </button>
        </div>

        <p className="login-link">
          Already have an account?{" "}
          <Link to="/">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}