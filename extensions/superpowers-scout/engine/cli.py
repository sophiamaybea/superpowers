"""CLI entry point using the exact same engine as the HTTP server.

This is the supported local skill-tool bridge. It does not install a global
ChatGPT interceptor or give ChatGPT access to a local runtime automatically.
"""
import argparse
import json
from .iterative import solve


def main(argv=None):
    parser=argparse.ArgumentParser(description='Superpowers Scout evidence-led research CLI')
    parser.add_argument('--prompt',required=True,help='Task description')
    parser.add_argument('--failure',default='',help='Observed error or mismatch')
    parser.add_argument('--max-rounds',type=int,default=4,choices=range(1,7),metavar='1..6')
    parser.add_argument('--strict',action='store_true')
    parser.add_argument('--no-model',action='store_true',help='Research and make a deterministic brief without model calls')
    args=parser.parse_args(argv)
    print(json.dumps(solve(args.prompt,failure=args.failure,max_rounds=args.max_rounds,
            strict=args.strict,generate=not args.no_model,refine_prompt=not args.no_model),indent=2))

if __name__=='__main__':main()
