import os
import requests
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageTk
from io import BytesIO
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# Replace these with your actual API keys
GROQ_API_KEY = ""  # Replace with your actual key
YOUTUBE_API_KEY = ""  # Replace with your actual key

# Initialize AI client
groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Modern color scheme
COLORS = {
    "background": "#2d2d2d",
    "primary": "#4a6fa5",
    "secondary": "#3a3a3a",
    "text": "#ffffff",
    "highlight": "#6b8cce",
    "success": "#4caf50",
    "error": "#f44336",
    "progress": "#ff9800"
}

def get_video_details(video_id):
    """Fetch video title and thumbnail from YouTube API."""
    try:
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("items"):
            return None, None
            
        snippet = data["items"][0]["snippet"]
        title = snippet["title"]
        thumbnail_url = snippet["thumbnails"]["high"]["url"]
        return title, thumbnail_url
        
    except Exception as e:
        print(f"Error fetching video details: {e}")
        return None, None

def get_english_transcript(video_id):
    """Fetch English transcript from YouTube video."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try manual English transcript first
        try:
            transcript = transcript_list.find_transcript(['en','hi','mr'])
        except:
            # Fall back to generated transcript
            transcript = transcript_list.find_generated_transcript(['en'])
            
        return " ".join([part['text'] for part in transcript.fetch()])
        
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def summarize_transcript(transcript):
    """Send transcript to AI for summarization."""
    try:
        system_prompt = "You are an expert content summarizer. Create a concise summary with key points."
        user_prompt = f"""Please summarize this video transcript into:
        1. A brief overview (2-3 sentences)
        2. 5-7 key bullet points
        3. Important takeaways
        
        Transcript: {transcript[:15000]}"""  # Limit to 15k chars to avoid token limits
        
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6,
            max_tokens=1024
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error generating summary: {e}"

def on_submit():
    """Handle submit button click event."""
    video_id = entry_video_id.get().strip()
    if not video_id:
        messagebox.showwarning("Input Error", "Please enter a YouTube Video ID")
        return
    
    try:
        # Clear previous results
        label_video_title.config(text="")
        label_thumbnail.config(image="")
        text_summary.delete(1.0, tk.END)
        
        # Step 1: Get video details
        update_progress("Fetching video info...")
        title, thumbnail_url = get_video_details(video_id)
        
        if not title:
            messagebox.showerror("Error", "Couldn't fetch video details. Check:\n1. Video ID\n2. YouTube API key")
            return
            
        label_video_title.config(text=title)
        
        # Load thumbnail if available
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url, timeout=10)
                img_data = Image.open(BytesIO(response.content))
                img_data = img_data.resize((320, 180), Image.LANCZOS)
                img = ImageTk.PhotoImage(img_data)
                label_thumbnail.config(image=img)
                label_thumbnail.image = img
            except Exception as e:
                print(f"Couldn't load thumbnail: {e}")
        
        # Step 2: Get transcript
        update_progress("Fetching transcript...")
        transcript = get_english_transcript(video_id)
        
        if not transcript:
            messagebox.showerror("Error", "No English transcript available for this video")
            return
            
        # Step 3: Generate summary
        update_progress("Generating summary...")
        summary = summarize_transcript(transcript)
        
        if not summary or "Error" in summary:
            messagebox.showerror("Error", f"Summary failed: {summary}")
            return
            
        text_summary.delete(1.0, tk.END)
        text_summary.insert(tk.END, summary)
        update_progress("Done!", success=True)
        
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        update_progress("")

def update_progress(message, success=False):
    """Update progress label with colored text"""
    progress_label.config(text=message)
    if success:
        progress_label.config(foreground=COLORS["success"])
    else:
        progress_label.config(foreground=COLORS["progress"])
    root.update()

def copy_to_clipboard():
    """Copy summary to clipboard"""
    root.clipboard_clear()
    root.clipboard_append(text_summary.get(1.0, tk.END))
    messagebox.showinfo("Copied", "Summary copied to clipboard!")

def clear_all():
    """Clear all fields"""
    entry_video_id.delete(0, tk.END)
    label_video_title.config(text="")
    label_thumbnail.config(image="")
    text_summary.delete(1.0, tk.END)
    progress_label.config(text="")

# Create main window
root = tk.Tk()
root.title("YouTube Summary Pro")
root.geometry("900x800")
root.configure(bg=COLORS["background"])

# Custom styles
style = ttk.Style()
style.theme_use('clam')

# Configure styles
style.configure("TFrame", background=COLORS["background"])
style.configure("TLabel", background=COLORS["background"], foreground=COLORS["text"], font=("Segoe UI", 10))
style.configure("TButton", 
                font=("Segoe UI", 10, "bold"), 
                padding=8,
                background=COLORS["primary"],
                foreground=COLORS["text"],
                borderwidth=0)
style.map("TButton",
          background=[('active', COLORS["highlight"]), ('pressed', COLORS["secondary"])],
          foreground=[('active', COLORS["text"])])

style.configure("TEntry", 
                fieldbackground=COLORS["secondary"],
                foreground=COLORS["text"],
                insertcolor=COLORS["text"],
                borderwidth=1,
                relief="flat",
                padding=5)

# Main container
main_frame = ttk.Frame(root, padding="20")
main_frame.pack(fill=tk.BOTH, expand=True)

# Header
header_frame = ttk.Frame(main_frame)
header_frame.pack(fill=tk.X, pady=(0, 20))

ttk.Label(header_frame, 
          text="YouTube Summary Pro", 
          font=("Segoe UI", 18, "bold"),
          foreground=COLORS["highlight"]).pack()

ttk.Label(header_frame, 
          text="Get AI-powered summaries of YouTube videos",
          font=("Segoe UI", 10)).pack()

# Input section
input_frame = ttk.Frame(main_frame, style="TFrame")
input_frame.pack(fill=tk.X, pady=10)

ttk.Label(input_frame, 
          text="YouTube Video ID or URL:", 
          font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

entry_video_id = ttk.Entry(input_frame, width=50, font=("Segoe UI", 10))
entry_video_id.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

btn_submit = ttk.Button(input_frame, text="Summarize", command=on_submit)
btn_submit.pack(side=tk.LEFT, padx=5)

# Progress indicator
progress_label = ttk.Label(main_frame, 
                          text="", 
                          font=("Segoe UI", 9),
                          foreground=COLORS["progress"])
progress_label.pack(pady=5)

# Video info display
video_frame = ttk.Frame(main_frame, style="TFrame")
video_frame.pack(fill=tk.X, pady=10)

label_video_title = ttk.Label(video_frame, 
                             text="", 
                             font=("Segoe UI", 12, "bold"), 
                             wraplength=700,
                             justify="center")
label_video_title.pack(pady=5)

label_thumbnail = ttk.Label(video_frame)
label_thumbnail.pack(pady=10)

# Summary section
summary_header = ttk.Frame(main_frame)
summary_header.pack(fill=tk.X, pady=(20, 5))

ttk.Label(summary_header, 
          text="AI Summary", 
          font=("Segoe UI", 14, "bold"),
          foreground=COLORS["highlight"]).pack(side=tk.LEFT)

btn_copy = ttk.Button(summary_header, 
                     text="📋 Copy", 
                     command=copy_to_clipboard,
                     style="TButton")
btn_copy.pack(side=tk.RIGHT, padx=5)

btn_clear = ttk.Button(summary_header, 
                      text="🗑️ Clear", 
                      command=clear_all,
                      style="TButton")
btn_clear.pack(side=tk.RIGHT, padx=5)

# Custom text widget with better styling
text_frame = ttk.Frame(main_frame)
text_frame.pack(fill=tk.BOTH, expand=True)

text_summary = scrolledtext.ScrolledText(
    text_frame, 
    width=85, 
    height=20, 
    wrap=tk.WORD, 
    font=("Segoe UI", 10),
    padx=15,
    pady=15,
    bg=COLORS["secondary"],
    fg=COLORS["text"],
    insertbackground=COLORS["text"],
    selectbackground=COLORS["highlight"],
    relief="flat",
    bd=0
)
text_summary.pack(fill=tk.BOTH, expand=True)

# Footer
footer_frame = ttk.Frame(main_frame, style="TFrame")
footer_frame.pack(fill=tk.X, pady=(20, 0))

ttk.Label(footer_frame, 
          text="© 2023 YouTube Summary Pro", 
          font=("Segoe UI", 8),
          foreground="#aaaaaa").pack(side=tk.RIGHT)

root.mainloop()
