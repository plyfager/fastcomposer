# Some part of this gradio demo code come from https://github.com/csyxwei/ELITE/blob/main/app_gradio.py
# Apache-2.0 License

from pipeline import convert_model_to_pipeline
from fastcomposer.utils import parse_args
from accelerate import Accelerator
import numpy as np
import gradio as gr
import torch
import PIL

class ModelWrapper:
    def __init__(self, model):
        super().__init__()
        self.model = model

    def inference(self, 
        image1: PIL.Image.Image,
        image2: PIL.Image.Image,
        prompt: str,
        seed: int,
        guidance_scale: float,
        alpha_: float,
        num_steps: int
    ):

        image = []
        if image1 != None: 
            image.append(image1)

        if image2 != None: 
            image.append(image2)
        
        if len(image) == 0:
            return [], "You need to upload at least one image."
        
        num_subject_in_text = (np.array(self.model.special_tokenizer.encode(prompt)) == self.model.image_token_id).sum()
        if num_subject_in_text != len(image):
            return [], f"Number of subjects in the text description doesn't match the number of reference images, #text subjects: {num_subject_in_text} #reference image: {len(image)}"

        if seed == -1:
            seed = np.random.randint(0, 1000000)

        generator = torch.manual_seed(seed)

        return self.model(
            prompt=prompt,
            height=512,
            width=512,
            num_inference_steps=num_steps,
            guidance_scale=guidance_scale,
            num_images_per_prompt=4,
            generator=generator,
            alpha_=alpha_,
            reference_subject_images=image  
        ).images, "run successfully" 
        

def create_demo():
    TITLE = '# [FastComposer Demo](https://github.com/mit-han-lab/fastcomposer)'

    DESCRIPTION = '''To run the demo, you should:   
    1. Upload your images. The order of image1 and image2 needs to match the order of the subects in the prompt. You only need 1 image for single subject generation.   
    2. Input proper text prompts, such as "A woman <A*> and a man <A*> in the snow" or "A painting of a man <A*> in the style of Van Gogh", where "<A*>" specifies the token you want to augment and comes after the word.   
    3. Click the Run button. You can also adjust the hyperparameters to improve the results. Look at the job status to see if there are any errors with your input.
    '''
    args = parse_args()
    accelerator = Accelerator(
        mixed_precision=args.mixed_precision,
    )

    model = ModelWrapper(convert_model_to_pipeline(args, accelerator.device))

    with gr.Blocks() as demo:
        gr.Markdown(TITLE)
        gr.Markdown(DESCRIPTION)
        with gr.Row():
            with gr.Column():
                with gr.Box():
                    image1 = gr.Image(label='Image 1', type='pil')
                    image2 = gr.Image(label='Image 2', type='pil')

                    gr.Markdown(
                        'Upload the image for your subject')
                prompt = gr.Text(
                    label='Prompt',
                    placeholder='e.g. "A woman <A*> and a man <A*> in the snow", "A painting of a man <A*> in the style of Van Gogh"',
                    info='Use "<A*>" to specify the word you want to augment.')
                alpha_ = gr.Slider(
                    label='alpha',
                    minimum=0,
                    maximum=1,
                    step=0.05,
                    value=0.7,
                    info='A smaller alpha aligns images with text better, but may deviate from the subject image. Increase alpha to improve identity preservation, decrease it for prompt consistency.'
                )
                run_button = gr.Button('Run')
                with gr.Accordion(label='Advanced options', open=False):
                    seed = gr.Slider(
                        label='Seed',
                        minimum=-1,
                        maximum=1000000,
                        step=1,
                        value=-1,
                        info=
                        'If set to -1, a different seed will be used each time.'
                    )
                    guidance_scale = gr.Slider(label='Guidance scale',
                                               minimum=1.5,
                                               maximum=50,
                                               step=0.1,
                                               value=5.0)
                    num_steps = gr.Slider(
                        label='Steps',
                        minimum=1,
                        maximum=300,
                        step=1,
                        value=50,
                    )
            with gr.Column():
                result = gr.Gallery(label='Generated Images').style(grid=[2], height="auto")
                error_message = gr.Text(label='Job Status')

        inputs = [
            image1, 
            image2,
            prompt,
            seed,
            guidance_scale,
            alpha_,
            num_steps,
        ]
        run_button.click(fn=model.inference, inputs=inputs, outputs=[result, error_message])
    return demo


if __name__ == '__main__':
    demo = create_demo()
    demo.queue(api_open=False).launch(share=True, show_error=True)
