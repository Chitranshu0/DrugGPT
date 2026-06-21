import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config({path:"../.env"});

const PORT = process.env.EXPRESS_SERVER_PORT || 3000;
const RAG_ENDPOINT = process.env.RAG_ENDPOINT;

const BASE_PATH = import.meta.dirname;

const app = express();

app.use(express.json());
app.use(cors());

app.use(express.static(path.join(BASE_PATH, 'public')));

app.post('/chat-completion', async (req, res) => {
    try{
        const response = await fetch(RAG_ENDPOINT, {
            method:"POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({message: req.body.message})
        });
        const answer = await response.json();
        return res.json({ role: "bot", message: answer.answer });
    }
    catch(error) {
        console.log("Error:", error.message);
    }
    return res.json({ role: "error", message: "Unable to generate response." });

});

app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
});
