document.addEventListener('DOMContentLoaded', () => {
    // Chatbot Toggle
    const trigger = document.getElementById('chatbot-trigger');
    const widget = document.getElementById('chatbot-widget');
    const closeBtn = document.getElementById('close-chat');

    trigger.addEventListener('click', () => {
        widget.classList.toggle('chatbot-closed');
    });

    closeBtn.addEventListener('click', () => {
        widget.classList.add('chatbot-closed');
    });

    // Chat Logic
    const sendBtn = document.getElementById('send-msg');
    const input = document.querySelector('.chat-input input');
    const messages = document.getElementById('chat-messages');

    const addMessage = (text, isBot = false) => {
        const msg = document.createElement('div');
        msg.className = `message ${isBot ? 'bot-message' : 'user-message'}`;
        msg.textContent = text;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
    };

    const handleSend = async () => {
        const text = input.value.trim();
        if (text) {
            addMessage(text);
            input.value = '';
            
            // Show loading bubble
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'message bot-message loading';
            loadingMsg.textContent = 'Typing...';
            messages.appendChild(loadingMsg);
            messages.scrollTop = messages.scrollHeight;

            try {
                // Call local backend (if running)
                const response = await fetch('http://localhost:8000/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                
                const data = await response.json();
                messages.removeChild(loadingMsg);
                addMessage(data.response, true);
            } catch (err) {
                messages.removeChild(loadingMsg);
                // Fallback to simulation if backend is not reachable
                setTimeout(() => {
                    const responses = [
                        "I'd be happy to help you with your AI project! I noticed you might be interested in our AI Audit.",
                        "Our expertise in OCR can definitely scale your operations globally.",
                        "We specialize in LangGraph for complex agentic workflows in the US and Europe.",
                        "Nexus delivers premium solutions in Python and Go for international clients.",
                        "Let's book a discovery call to discuss your regional RAG implementation."
                    ];
                    const rand = Math.floor(Math.random() * responses.length);
                    addMessage(responses[rand], true);
                }, 1000);
            }
        }
    };

    sendBtn.addEventListener('click', handleSend);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    // Scroll Animations
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.service-card, .tech-group, .blog-card, .case-card, .reach-item, .contact-container').forEach(el => {
        observer.observe(el);
    });

    // Form Submissions
    const contactForm = document.getElementById('contact-form');
    const newsletterForm = document.getElementById('newsletter-form');

    const handleFormSubmit = (e, msg) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        const originalText = btn.textContent;
        
        btn.textContent = 'Sending...';
        btn.disabled = true;

        setTimeout(() => {
            btn.textContent = 'Success!';
            btn.style.background = '#10b981';
            alert(msg);
            e.target.reset();

            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
                btn.disabled = false;
            }, 3000);
        }, 1500);
    };

    if (contactForm) {
        contactForm.addEventListener('submit', (e) => handleFormSubmit(e, 'Message sent successfully! We will get back to you soon.'));
    }

    if (newsletterForm) {
        newsletterForm.addEventListener('submit', (e) => handleFormSubmit(e, 'Thanks for subscribing to our newsletter!'));
    }
});
