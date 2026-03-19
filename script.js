document.addEventListener('DOMContentLoaded', () => {
    // Dynamic Card Rendering
    async function renderDynamicContent() {
        try {
            const response = await fetch('content.json');
            const data = await response.json();

            // Render Blogs
            const blogGrid = document.querySelector('.blog-grid');
            if (blogGrid) {
                blogGrid.innerHTML = data.blogs.map(blog => `
                    <div class="blog-card">
                        <div class="blog-img" style="background: linear-gradient(135deg, #8b5cf6, #3b82f6);"></div>
                        <div class="blog-content">
                            <h3>${blog.title}</h3>
                            <p>${blog.subtitle}</p>
                            <a href="post.html?blog=${blog.id}" class="read-more">Read Insight <i class="fas fa-arrow-right"></i></a>
                        </div>
                    </div>
                `).join('');
            }

            // Render Case Studies
            const caseGrid = document.querySelector('.cases-grid');
            if (caseGrid) {
                caseGrid.innerHTML = data.cases.map(study => `
                    <div class="case-card">
                        <div class="case-header">
                            <span class="case-badge">Impact Analysis</span>
                            <h3>${study.title}</h3>
                        </div>
                        <p>${study.subtitle}</p>
                        <a href="study.html?id=${study.id}" class="read-more">View Full Breakdown <i class="fas fa-arrow-right"></i></a>
                    </div>
                `).join('');
            }

            // Re-apply observer to new elements
            document.querySelectorAll('.blog-card, .case-card').forEach(el => observer.observe(el));
        } catch (err) {
            console.warn('Failed to load dynamic content:', err);
        }
    }
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
                const response = await fetch('https://nexus-intelgithubio-production.up.railway.app/chat', {
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

    document.querySelectorAll('.service-card, .tech-group, .blog-card, .case-card, .contact-container').forEach(el => {
        observer.observe(el);
    });

    // Form Submissions
    const contactForm = document.getElementById('contact-form');
    const newsletterForm = document.getElementById('newsletter-form');

    const handleFormSubmit = async (e, endpoint, successMsg) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        const originalText = btn.textContent;
        
        // Extract data
        const formData = {};
        const inputs = e.target.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            const label = input.previousElementSibling ? input.previousElementSibling.textContent.toLowerCase() : 'email';
            formData[label] = input.value;
        });

        btn.textContent = 'Sending...';
        btn.disabled = true;

        try {
            const response = await fetch(`https://nexus-intelgithubio-production.up.railway.app/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!response.ok) throw new Error('Backend unavailable');

            btn.textContent = 'Success!';
            btn.style.background = '#10b981';
            alert(successMsg);
            e.target.reset();
        } catch (err) {
            console.warn('Form submission fallback:', err);
            // Simulate success for demo purposes if backend is down
            setTimeout(() => {
                btn.textContent = 'Success (Demo)!';
                btn.style.background = '#3b82f6';
                alert(successMsg + ' (Simulation Mode)');
                e.target.reset();
            }, 1000);
        } finally {
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
                btn.disabled = false;
            }, 3000);
        }
    };

    if (contactForm) {
        contactForm.addEventListener('submit', (e) => handleFormSubmit(e, 'contact', 'Message sent successfully! We will get back to you soon.'));
    }

    if (newsletterForm) {
        newsletterForm.addEventListener('submit', (e) => handleFormSubmit(e, 'newsletter', 'Thanks for subscribing to our newsletter!'));
    }

    // ROI Calculator Logic
    const volInput = document.getElementById('doc-volume');
    const costInput = document.getElementById('unit-cost');
    const volVal = document.getElementById('vol-val');
    const costVal = document.getElementById('cost-val');
    const savingsTotal = document.getElementById('savings-total');

    if (volInput && costInput) {
        const calculateROI = () => {
            const vol = parseInt(volInput.value);
            const cost = parseFloat(costInput.value);
            
            volVal.textContent = vol.toLocaleString();
            costVal.textContent = cost.toFixed(2);
            
            // Assume 80% cost reduction with AI
            const manualAnnual = vol * cost * 12;
            const aiAnnual = manualAnnual * 0.2;
            const savings = manualAnnual - aiAnnual;
            
            savingsTotal.textContent = `$${Math.round(savings).toLocaleString()}`;
        };

        volInput.addEventListener('input', calculateROI);
        costInput.addEventListener('input', calculateROI);
        calculateROI(); // Initial calc
    }

    renderDynamicContent();
});
